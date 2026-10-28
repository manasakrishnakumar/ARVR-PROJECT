import os
import tempfile

os.environ.setdefault("ARVR_DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/rl.db")

import pytest
from fastapi.testclient import TestClient

from app.api import auth
from app.database.db import reset_db
from app.main import app

PW = "correct horse 1"


@pytest.fixture
def c():
    reset_db()
    auth._failures.clear()
    clock = {"t": 1000.0}
    auth._now = lambda: clock["t"]
    with TestClient(app) as client:
        client.clock = clock  # type: ignore[attr-defined]
        yield client
    auth._now = __import__("time").monotonic
    auth._failures.clear()


def bad(c, name="alice"):
    return c.post("/api/auth/login", json={"username": name, "password": "wrong password 1"})


def test_repeated_failures_lock_the_account_even_for_the_correct_password(c):
    c.post("/api/auth/register", json={"username": "alice", "password": PW})
    assert [bad(c).status_code for _ in range(auth.MAX_FAILURES)] == [401] * auth.MAX_FAILURES
    locked = c.post("/api/auth/login", json={"username": "alice", "password": PW})
    assert locked.status_code == 429 and int(locked.headers["retry-after"]) > 0
    assert bad(c).status_code == 429


def test_lock_expires_after_the_window_and_success_resets_the_counter(c):
    c.post("/api/auth/register", json={"username": "alice", "password": PW})
    for _ in range(auth.MAX_FAILURES):
        bad(c)
    c.clock["t"] += auth.LOCKOUT_WINDOW_S + 1  # type: ignore[attr-defined]
    ok = c.post("/api/auth/login", json={"username": "alice", "password": PW})
    assert ok.status_code == 200
    for _ in range(auth.MAX_FAILURES - 1):  # the earlier failures no longer count
        assert bad(c).status_code == 401
    assert c.post("/api/auth/login", json={"username": "alice", "password": PW}).status_code == 200  # success clears the count
    assert [bad(c).status_code for _ in range(auth.MAX_FAILURES)] == [401] * auth.MAX_FAILURES


def test_other_users_are_unaffected_and_unknown_usernames_are_limited_too(c):
    c.post("/api/auth/register", json={"username": "alice", "password": PW})
    c.post("/api/auth/register", json={"username": "bobby", "password": PW})
    for _ in range(auth.MAX_FAILURES):
        bad(c, "alice")
    assert c.post("/api/auth/login", json={"username": "bobby", "password": PW}).status_code == 200
    codes = [bad(c, "nobody") for _ in range(auth.MAX_FAILURES + 1)]
    assert [r.status_code for r in codes] == [401] * auth.MAX_FAILURES + [429]  # no enumeration: same behaviour as a real account


def test_bounded_memory(c, monkeypatch):
    for i in range(10050):
        auth._failures[f"user{i}|x"] = auth.deque([1.0])
    bad(c, "trigger")
    assert len(auth._failures) < 10050
