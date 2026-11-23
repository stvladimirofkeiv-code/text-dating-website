from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .db import Base, engine, get_db
from .models import Conversation, Message, User
from .reveal import can_request_reveal, photos_unlocked
from .security import csrf_token, hash_password, verify_csrf, verify_password

MIN_FIRST_LETTER = 80
MAX_MESSAGE = 4000

app = FastAPI(title="Text First", docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=settings.is_prod,
    same_site="lax",
    max_age=60 * 60 * 24 * 14,
)
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["csrf_token"] = csrf_token


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'"
    return resp


@app.on_event("startup")
def init_db() -> None:
    # TODO: replace with Alembic migrations before real production use.
    Base.metadata.create_all(engine)


# ---------- helpers ----------
def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    uid = request.session.get("uid")
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def get_convo(db: Session, convo_id: int, me: User) -> Conversation:
    c = db.get(Conversation, convo_id)
    if not c or me.id not in (c.user_low_id, c.user_high_id):
        raise HTTPException(404)
    return c


def counts(c: Conversation) -> tuple[int, int]:
    low = sum(1 for m in c.messages if m.sender_id == c.user_low_id)
    high = sum(1 for m in c.messages if m.sender_id == c.user_high_id)
    return low, high


# ---------- public ----------
@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def index(request: Request):
    return redirect("/discover" if request.session.get("uid") else "/login")


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.post("/register", dependencies=[Depends(verify_csrf)])
def register(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    display_name = display_name.strip()[:50]
    err = None
    if "@" not in email or len(email) > 255:
        err = "Enter a valid email."
    elif not display_name:
        err = "Choose a display name (a first name or nickname)."
    elif len(password) < 10:
        err = "Password must be at least 10 characters."
    if err:
        return templates.TemplateResponse(request, "register.html", {"error": err}, status_code=400)
    user = User(email=email, display_name=display_name, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "register.html", {"error": "That email is already registered."}, status_code=400
        )
    request.session.clear()
    request.session["uid"] = user.id
    return redirect("/profile")


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login", dependencies=[Depends(verify_csrf)])
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Wrong email or password."}, status_code=400
        )
    request.session.clear()
    request.session["uid"] = user.id
    return redirect("/discover")


@app.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    request.session.clear()
    return redirect("/login")


# ---------- profile ----------
@app.get("/profile", response_class=HTMLResponse)
def profile_form(request: Request, me: User = Depends(current_user)):
    return templates.TemplateResponse(request, "profile.html", {"me": me, "saved": False})


@app.post("/profile", dependencies=[Depends(verify_csrf)])
def profile_save(
    request: Request,
    age: int = Form(...),
    city: str = Form(""),
    bio: str = Form(""),
    looking_for: str = Form(""),
    me: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if age < 18 or age > 120:
        raise HTTPException(400, "You must be 18 or older.")
    me.age, me.city, me.bio, me.looking_for = age, city.strip()[:100], bio.strip()[:3000], looking_for.strip()[:1500]
    db.add(me)
    db.commit()
    return templates.TemplateResponse(request, "profile.html", {"me": me, "saved": True})


# ---------- discover / letters ----------
@app.get("/discover", response_class=HTMLResponse)
def discover(request: Request, me: User = Depends(current_user), db: Session = Depends(get_db)):
    talking = select(Conversation.user_low_id).where(Conversation.user_high_id == me.id).union(
        select(Conversation.user_high_id).where(Conversation.user_low_id == me.id)
    )
    people = db.scalars(
        select(User)
        .where(User.id != me.id, User.age.is_not(None), User.bio != "", User.id.not_in(talking))
        .order_by(func.random())
        .limit(20)
    ).all()
    return templates.TemplateResponse(request, "discover.html", {"me": me, "people": people})


@app.get("/people/{user_id}", response_class=HTMLResponse)
def person(request: Request, user_id: int, me: User = Depends(current_user), db: Session = Depends(get_db)):
    other = db.get(User, user_id)
    if not other or other.id == me.id:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "person.html", {"me": me, "p": other, "min_len": MIN_FIRST_LETTER, "error": None}
    )


@app.post("/people/{user_id}/letter", dependencies=[Depends(verify_csrf)])
def first_letter(
    request: Request,
    user_id: int,
    body: str = Form(...),
    me: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    other = db.get(User, user_id)
    if not other or other.id == me.id:
        raise HTTPException(404)
    body = body.strip()
    if len(body) < MIN_FIRST_LETTER or len(body) > MAX_MESSAGE:
        return templates.TemplateResponse(
            request,
            "person.html",
            {"me": me, "p": other, "min_len": MIN_FIRST_LETTER,
             "error": f"Write a real first letter (at least {MIN_FIRST_LETTER} characters)."},
            status_code=400,
        )
    lo, hi = pair(me.id, other.id)
    convo = db.scalar(select(Conversation).where(Conversation.user_low_id == lo, Conversation.user_high_id == hi))
    if not convo:
        convo = Conversation(user_low_id=lo, user_high_id=hi)
        db.add(convo)
        db.flush()
    db.add(Message(conversation_id=convo.id, sender_id=me.id, body=body))
    db.commit()
    return redirect(f"/c/{convo.id}")


# ---------- conversations ----------
@app.get("/inbox", response_class=HTMLResponse)
def inbox(request: Request, me: User = Depends(current_user), db: Session = Depends(get_db)):
    convos = db.scalars(
        select(Conversation)
        .where(or_(Conversation.user_low_id == me.id, Conversation.user_high_id == me.id))
        .order_by(Conversation.id.desc())
    ).all()
    rows = []
    for c in convos:
        other_id = c.user_high_id if c.user_low_id == me.id else c.user_low_id
        rows.append({"c": c, "other": db.get(User, other_id), "last": c.messages[-1] if c.messages else None})
    return templates.TemplateResponse(request, "inbox.html", {"me": me, "rows": rows})


@app.get("/c/{convo_id}", response_class=HTMLResponse)
def thread(request: Request, convo_id: int, me: User = Depends(current_user), db: Session = Depends(get_db)):
    c = get_convo(db, convo_id, me)
    other = db.get(User, c.user_high_id if c.user_low_id == me.id else c.user_low_id)
    low, high = counts(c)
    mine, theirs = (low, high) if c.user_low_id == me.id else (high, low)
    i_want, they_want = (
        (c.low_wants_reveal, c.high_wants_reveal) if c.user_low_id == me.id
        else (c.high_wants_reveal, c.low_wants_reveal)
    )
    ctx = {
        "me": me, "other": other, "c": c, "mine": mine, "theirs": theirs,
        "min_each": settings.min_messages_each,
        "can_reveal": can_request_reveal(mine, theirs, settings.min_messages_each),
        "i_want": i_want, "they_want": they_want,
        "unlocked": photos_unlocked(low, high, c.low_wants_reveal, c.high_wants_reveal, settings.min_messages_each),
    }
    return templates.TemplateResponse(request, "thread.html", ctx)


@app.post("/c/{convo_id}/send", dependencies=[Depends(verify_csrf)])
def send(convo_id: int, body: str = Form(...), me: User = Depends(current_user), db: Session = Depends(get_db)):
    c = get_convo(db, convo_id, me)
    body = body.strip()
    if body and len(body) <= MAX_MESSAGE:
        db.add(Message(conversation_id=c.id, sender_id=me.id, body=body))
        db.commit()
    return redirect(f"/c/{c.id}")


@app.post("/c/{convo_id}/reveal", dependencies=[Depends(verify_csrf)])
def reveal(convo_id: int, me: User = Depends(current_user), db: Session = Depends(get_db)):
    c = get_convo(db, convo_id, me)
    low, high = counts(c)
    mine, theirs = (low, high) if c.user_low_id == me.id else (high, low)
    if not can_request_reveal(mine, theirs, settings.min_messages_each):
        raise HTTPException(400, "Keep talking first: you both need to write more.")
    if c.user_low_id == me.id:
        c.low_wants_reveal = True
    else:
        c.high_wants_reveal = True
    db.commit()
    return redirect(f"/c/{c.id}")
