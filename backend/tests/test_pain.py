import os
import tempfile

os.environ.setdefault("ARVR_DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/pain.db")

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.database.db import reset_db
from app.exercises.library import get_exercise
from app.main import app
from app.personalization.controller import AdaptiveConfig, HistoryItem, PainRule, RepObs, recommend

CFG = AdaptiveConfig.load()
LEVELS = get_exercise("elbow_flexion").difficulty_levels


def good(n=6):
    return [RepObs(label="acceptable", score=0.95, reliable=True, counted=True, peak_progress=0.9) for _ in range(n)]


def two_good():
    return [HistoryItem(level=1, classification="good")]


def test_without_pain_two_good_sessions_raise_the_level():
    assert recommend(CFG, LEVELS, 1, good(), two_good()).action == "increase"


def test_moderate_pain_blocks_an_increase_and_says_why():
    r = recommend(CFG, LEVELS, 1, good(), two_good(), pain=CFG.pain.no_increase_at)
    assert r.action == "maintain" and r.next_level == 1 and any("pain" in x for x in r.reasons)


def test_high_pain_pauses_even_after_a_good_session_and_never_raises():
    r = recommend(CFG, LEVELS, 1, good(), two_good(), pain=CFG.pain.pause_at)
    assert r.action == "pause" and r.next_level == 1 and "professional" in " ".join(r.reasons)


def test_high_pain_pauses_with_too_little_data():
    r = recommend(CFG, LEVELS, 1, [], [], pain=9)
    assert r.action == "pause"


def test_low_pain_changes_nothing():
    assert recommend(CFG, LEVELS, 1, good(), two_good(), pain=1).action == "increase"


def test_pain_thresholds_must_be_ordered():
    with pytest.raises(ValidationError):
        PainRule(no_increase_at=8, pause_at=3)


@pytest.fixture
def c():
    reset_db()
    with TestClient(app) as client:
        yield client


def test_api_stores_pain_and_note_and_applies_the_rule(c):
    s = c.post("/api/sessions", json={"exercise_id": "elbow_flexion", "difficulty": 1}).json()
    c.post(f"/api/sessions/{s['id']}/repetitions", json=[{"index": i, "label": "acceptable", "score": 0.95, "counted": True} for i in range(1, 7)])
    r = c.post(f"/api/sessions/{s['id']}/complete", json={"pain": 8, "note": "shoulder twinge"}).json()
    assert r["recommendation"]["action"] == "pause"
    assert r["session"]["pain"] == 8 and r["session"]["note"] == "shoulder twinge"


def test_api_complete_still_works_without_a_body_and_rejects_bad_pain(c):
    s = c.post("/api/sessions", json={"exercise_id": "elbow_flexion"}).json()
    assert c.post(f"/api/sessions/{s['id']}/complete", json={"pain": 11}).status_code == 422
    assert c.post(f"/api/sessions/{s['id']}/complete").status_code == 200


def test_checkin_after_completion_updates_the_decision_and_summary(c):
    tok = c.post("/api/auth/register", json={"username": "painuser", "password": "correct horse 1"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    s = c.post("/api/sessions", json={"exercise_id": "elbow_flexion", "difficulty": 1}, headers=h).json()
    c.post(f"/api/sessions/{s['id']}/repetitions", headers=h, json=[{"index": i, "label": "acceptable", "score": 0.95, "counted": True} for i in range(1, 7)])
    assert c.post(f"/api/sessions/{s['id']}/complete", headers=h).json()["recommendation"]["action"] == "maintain"
    r = c.post(f"/api/sessions/{s['id']}/checkin", headers=h, json={"pain": 9, "note": "sharp"}).json()
    assert r["recommendation"]["action"] == "pause"
    d = c.get(f"/api/sessions/{s['id']}/detail", headers=h).json()
    assert d["decision"]["action"] == "pause" and d["pain"] == 9
    assert c.get("/api/adaptation/state", params={"exercise_id": "elbow_flexion"}, headers=h).json()["last_action"] == "pause"


def test_checkin_before_completion_is_refused_and_other_users_cannot_check_in(c):
    s = c.post("/api/sessions", json={"exercise_id": "elbow_flexion"}).json()
    assert c.post(f"/api/sessions/{s['id']}/checkin", json={"pain": 2}).status_code == 409
