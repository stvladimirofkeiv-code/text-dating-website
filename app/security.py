import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import HTTPException, Request

_ph = PasswordHasher()


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, pw)
    except (VerifyMismatchError, InvalidHashError):
        return False


def csrf_token(request: Request) -> str:
    tok = request.session.get("csrf")
    if not tok:
        tok = secrets.token_urlsafe(32)
        request.session["csrf"] = tok
    return tok


async def verify_csrf(request: Request) -> None:
    form = await request.form()
    sent = str(form.get("csrf", ""))
    expected = request.session.get("csrf", "")
    if not expected or not secrets.compare_digest(sent, expected):
        raise HTTPException(status_code=403, detail="Bad CSRF token")
