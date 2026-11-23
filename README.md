# Text First (text-dating-website)

A dating app where **words come first**. Profiles are text only. Photos stay locked until
both people have written a minimum number of messages **and** both explicitly opt in.

## Run locally
```bash
#!/usr/bin/env bash
set -e

# System packages
sudo apt update
sudo apt install -y git curl python3 python3-venv python3-pip build-essential libpq-dev

# Docker (optional, for docker compose + Postgres)
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker "$USER"   # log out/in afterwards

# VS Code (needed for Cline; skip if you use Remote-SSH from your own machine)
sudo snap install code --classic
code --install-extension saoudrizwan.claude-dev   # the Cline extension
```
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload      # uses SQLite (dev.db) by default
pytest
```
Or with Postgres: `cp .env.example .env && docker compose up --build`

## Design
- FastAPI + SQLAlchemy 2 + server-rendered Jinja templates (no JS needed)
- Argon2 password hashing, signed session cookies, CSRF tokens on every POST, security headers
- `app/reveal.py` holds the photo-unlock rule as pure, tested logic
- First letters must be 80+ characters, to discourage low-effort swiping

## Roadmap / before real production
- [ ] Alembic migrations (currently `create_all`)
- [ ] Rate limiting on login/register/messages; email verification; password reset
- [ ] Photo upload (object storage, EXIF stripping, moderation) shown only when unlocked
- [ ] Block/report, 18+ enforcement, privacy policy / ToS
- [ ] Matching preferences (age range, location), notifications
- [ ] Secrets via your host's secret manager; HTTPS (set `ENV=production`)
