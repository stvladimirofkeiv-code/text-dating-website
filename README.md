# Text First (text-dating-website)

A dating app where **words come first**. Profiles are text only. Photos stay locked until
both people have written a minimum number of messages **and** both explicitly opt in.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload      # uses SQLite (dev.db) by default
pytest
```
Or with Postgres: `cp .env.example .env && docker compose up --build`

## Design
- FastAPI + SQLAlchemy 2 + server-rendered Jinja templates (no JS needed)
- Responsive, accessible interface with a consistent editorial visual style and no externally hosted assets
- Argon2 password hashing, signed session cookies, CSRF tokens on every POST, security headers
- `app/reveal.py` holds the photo-unlock rule as pure, tested logic
- First letters must be 80+ characters, to discourage low-effort swiping

The visual refresh does not mean the service is production-ready. Complete the safeguards below before serving real users.

## Roadmap / before real production
- [ ] Alembic migrations (currently `create_all`)
- [ ] Rate limiting on login/register/messages; email verification; password reset
- [ ] Photo upload (object storage, EXIF stripping, moderation) shown only when unlocked
- [ ] Block/report, 18+ enforcement, privacy policy / ToS
- [ ] Matching preferences (age range, location), notifications
- [ ] Secrets via your host's secret manager; HTTPS (set `ENV=production`)
