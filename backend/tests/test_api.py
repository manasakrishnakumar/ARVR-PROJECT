import os, tempfile
os.environ["ARVR_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/t.db"

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_disclaimer():
    with TestClient(app) as c:
        r = c.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok" and "not a medical device" in r.json()["disclaimer"].lower()


def test_exercises_listed_and_unknown_404():
    with TestClient(app) as c:
        assert len(c.get("/api/exercises").json()) == 9
        assert c.get("/api/exercises/knee_flexion").status_code == 200
        assert c.get("/api/exercises/nope").status_code == 404


def test_session_create_and_validation():
    with TestClient(app) as c:
        r = c.post("/api/sessions", json={"exercise_id": "elbow_flexion", "is_demo": True})
        assert r.status_code == 201
        sid = r.json()["id"]
        assert c.get(f"/api/sessions/{sid}").json()["exercise_id"] == "elbow_flexion"
        assert c.get("/api/sessions/missing").status_code == 404
        assert c.post("/api/sessions", json={"exercise_id": "nope"}).status_code == 404
        assert c.post("/api/sessions", json={"exercise_id": "elbow_flexion", "difficulty": 99}).status_code == 422
