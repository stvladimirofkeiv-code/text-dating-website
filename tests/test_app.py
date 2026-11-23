import os
import re

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["MIN_MESSAGES_EACH"] = "1"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


@pytest.fixture()
def make_client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    def _make():
        c = TestClient(app, follow_redirects=False)
        return c

    yield _make
    Base.metadata.drop_all(engine)


def token(c, path):
    html = c.get(path).text
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def signup(c, email, name):
    r = c.post("/register", data={"email": email, "display_name": name, "password": "correct horse battery", "csrf": token(c, "/register")})
    assert r.status_code == 303
    r = c.post("/profile", data={"age": 30, "city": "X", "bio": "b" * 20, "looking_for": "y", "csrf": token(c, "/profile")})
    assert r.status_code == 200


def test_csrf_required(make_client):
    c = make_client()
    r = c.post("/login", data={"email": "a@b.c", "password": "x"})
    assert r.status_code == 403


def test_full_flow_unlocks_only_with_mutual_consent(make_client):
    a, b = make_client(), make_client()
    signup(a, "a@x.com", "Ann")
    signup(b, "b@x.com", "Bob")
    r = a.post("/people/2/letter", data={"body": "w" * 90, "csrf": token(a, "/people/2")})
    assert r.status_code == 303
    cid = r.headers["location"]
    b.post(cid + "/send", data={"body": "hello back", "csrf": token(b, cid)})
    a.post(cid + "/reveal", data={"csrf": token(a, cid)})
    assert "Photos are unlocked" not in a.get(cid).text
    b.post(cid + "/reveal", data={"csrf": token(b, cid)})
    assert "Photos are unlocked" in a.get(cid).text


def test_cannot_read_others_conversation(make_client):
    a, b, evil = make_client(), make_client(), make_client()
    signup(a, "a@x.com", "Ann"); signup(b, "b@x.com", "Bob"); signup(evil, "e@x.com", "Eve")
    cid = a.post("/people/2/letter", data={"body": "w" * 90, "csrf": token(a, "/people/2")}).headers["location"]
    assert evil.get(cid).status_code == 404
