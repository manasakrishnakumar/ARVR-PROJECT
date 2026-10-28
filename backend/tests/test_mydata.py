import os
import tempfile

os.environ.setdefault("ARVR_DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/mydata.db")

import pytest
from fastapi.testclient import TestClient

from app.database.db import reset_db
from app.main import app

PW = "correct horse 1"


@pytest.fixture
def c():
    reset_db()
    with TestClient(app) as client:
        yield client


def register(c, name):
    tok = c.post("/api/auth/register", json={"username": name, "password": PW}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def make_session(c, h, n=6, exercise="elbow_flexion", pain=None):
    s = c.post("/api/sessions", json={"exercise_id": exercise, "difficulty": 1}, headers=h).json()
    c.post(f"/api/sessions/{s['id']}/repetitions", headers=h,
           json=[{"index": i, "label": "acceptable", "score": 0.9, "counted": True, "features": {"rom_deg": 100.0, "duration_s": 2.0}} for i in range(1, n + 1)])
    body = {"pain": pain, "note": "ok"} if pain is not None else None
    c.post(f"/api/sessions/{s['id']}/complete", headers=h, **({"json": body} if body else {}))
    return s["id"]


def test_backup_then_restore_into_another_account_recreates_the_history(c):
    a = register(c, "alice")
    ids = [make_session(c, a), make_session(c, a, pain=3)]
    data = c.get("/api/me/backup", headers=a).json()
    assert data["version"] == 1 and [s["id"] for s in data["sessions"]] == ids
    assert data["sessions"][1]["pain"] == 3 and len(data["sessions"][0]["repetitions"]) == 6 and data["sessions"][0]["decision"]
    text = str(data)
    assert "password" not in text and "token" not in text

    c.delete("/api/me", headers=a)  # the first account is deleted, so the ids are free again
    b = register(c, "bobby")
    assert c.post("/api/me/restore", json=data, headers=b).json() == {"added": 2, "skipped": 0}
    assert c.post("/api/me/restore", json=data, headers=b).json() == {"added": 0, "skipped": 2}  # restoring twice duplicates nothing
    assert len(c.get("/api/sessions", headers=b).json()) == 2
    assert c.get("/api/adaptation/state", params={"exercise_id": "elbow_flexion"}, headers=b).json()["source"] == "history"
    assert c.get("/api/analytics/summary", headers=b).json()["total_sessions"] == 2


def test_restore_cannot_overwrite_another_accounts_sessions(c):
    a = register(c, "alice")
    sid = make_session(c, a)
    data = c.get("/api/me/backup", headers=a).json()
    b = register(c, "bobby")
    assert c.post("/api/me/restore", json=data, headers=b).json() == {"added": 0, "skipped": 1}
    assert c.get("/api/sessions", headers=b).json() == []
    assert c.get(f"/api/sessions/{sid}", headers=b).status_code == 404


def test_restore_validates_input(c):
    h = register(c, "alice")
    good = {"id": "a" * 32, "exercise_id": "elbow_flexion", "difficulty": 1, "started_at": "2026-01-01T10:00:00Z", "ended_at": "2026-01-01T10:05:00Z"}
    assert c.post("/api/me/restore", json={"version": 2, "sessions": []}, headers=h).status_code == 422
    assert c.post("/api/me/restore", json={"version": 1, "sessions": [{**good, "exercise_id": "nope"}]}, headers=h).status_code == 422
    assert c.post("/api/me/restore", json={"version": 1, "sessions": [{**good, "id": "bad id"}]}, headers=h).status_code == 422
    assert c.post("/api/me/restore", json={"version": 1, "sessions": [{**good, "pain": 11}]}, headers=h).status_code == 422
    dup = {**good, "repetitions": [{"index": 1}, {"index": 1}]}
    assert c.post("/api/me/restore", json={"version": 1, "sessions": [dup]}, headers=h).status_code == 422
    assert c.post("/api/me/restore", json={"version": 1, "sessions": [good]}, headers=h).json()["added"] == 1


def test_backup_and_weekly_need_sign_in_and_exclude_demo_sessions(c):
    assert c.get("/api/me/backup").status_code == 401
    assert c.get("/api/analytics/weekly").status_code == 401
    h = register(c, "alice")
    d = c.post("/api/sessions", json={"exercise_id": "elbow_flexion", "is_demo": True}, headers=h).json()
    c.post(f"/api/sessions/{d['id']}/complete", headers=h)
    assert c.get("/api/me/backup", headers=h).json()["sessions"] == []


def test_weekly_summary_counts_recent_activity_and_streak(c):
    h = register(c, "alice")
    assert c.get("/api/analytics/weekly", headers=h).json() | {"note": ""} == {
        "sessions_last_7_days": 0, "counted_repetitions_last_7_days": 0, "day_streak": 0, "active_days_last_7": 0, "note": ""}
    make_session(c, h, n=5)
    make_session(c, h, n=4)
    w = c.get("/api/analytics/weekly", headers=h).json()
    assert w["sessions_last_7_days"] == 2 and w["counted_repetitions_last_7_days"] == 9
    assert w["day_streak"] == 1 and w["active_days_last_7"] == 1  # both on the same day
    assert "recovery" in w["note"]
