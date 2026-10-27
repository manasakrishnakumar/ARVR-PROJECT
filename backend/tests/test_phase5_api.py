import os
import tempfile

os.environ.setdefault("ARVR_DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/p5.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from starlette.websockets import WebSocketDisconnect

from app.core.security import hash_password, verify_password
from app.database.db import AdaptiveDecision, AuthToken, ExerciseSession, Repetition, SessionLocal, User, reset_db
from app.main import app
from app.synthetic.sequences import make_sequence

PW = "correct horse 1"


@pytest.fixture
def c():
    reset_db()
    with TestClient(app) as client:
        yield client


def register(c, name="alice", pw=PW):
    r = c.post("/api/auth/register", json={"username": name, "password": pw})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def new_session(c, headers=None, exercise="elbow_flexion", level=1, demo=False):
    r = c.post("/api/sessions", json={"exercise_id": exercise, "difficulty": level, "is_demo": demo}, headers=headers or {})
    assert r.status_code == 201, r.text
    return r.json()


def stream(c, s, n_reps, exercise="elbow_flexion", level=1, depth=1.0, period=3.0, key=None):
    """Drive the live WebSocket with SYNTHETIC joint angles, as the browser would."""
    seq = make_sequence(160, 50, n_reps, period_s=period, fps=15, depth=depth)
    url = f"/api/ws/analysis?exercise_id={exercise}&difficulty={level}&session_id={s['id']}&key={key or s['ws_key']}"
    reps = []
    with c.websocket_connect(url) as ws:
        assert ws.receive_json()["saving"] is True
        for t, a in seq:
            ws.send_json({"t": t, "angle": a})
        states = 0
        while states < len(seq):
            m = ws.receive_json()
            states += m["type"] == "state"
            if m["type"] == "rep":
                reps.append(m)
    return reps


def complete(c, s, headers=None):
    return c.post(f"/api/sessions/{s['id']}/complete", headers=headers or {})


def play(c, headers, level=1, n=None, demo=False, **kw):
    n = n or {1: 6, 2: 9, 3: 11}[level]
    s = new_session(c, headers, level=level, demo=demo)
    stream(c, s, n, level=level, **kw)
    return s, complete(c, s, headers)


# ---- accounts and security ----------------------------------------------------------------------

def test_password_hashing_is_salted_scrypt_and_verifies():
    h1, h2 = hash_password(PW), hash_password(PW)
    assert h1 != h2 and h1.startswith("scrypt$") and PW not in h1
    assert verify_password(PW, h1) and not verify_password("wrong password", h1)
    assert not verify_password(PW, None) and not verify_password(PW, "garbage")


def test_register_login_logout_and_token_rules(c):
    h = register(c)
    with SessionLocal() as db:
        u = db.scalar(select(User))
        assert u.password_hash.startswith("scrypt$") and PW not in u.password_hash
        tok = h["Authorization"].split()[1]
        assert db.scalar(select(AuthToken).where(AuthToken.token_digest == tok)) is None  # raw token never stored
    assert c.get("/api/me", headers=h).json()["username"] == "alice"
    assert c.post("/api/auth/register", json={"username": "alice", "password": PW}).status_code == 409
    assert c.post("/api/auth/register", json={"username": "bob", "password": "short"}).status_code == 422
    assert c.post("/api/auth/register", json={"username": "b o b!", "password": PW}).status_code == 422
    bad = c.post("/api/auth/login", json={"username": "alice", "password": "nope nope nope"})
    ghost = c.post("/api/auth/login", json={"username": "nobody", "password": "nope nope nope"})
    assert bad.status_code == ghost.status_code == 401 and bad.json() == ghost.json()  # no username enumeration
    tok2 = c.post("/api/auth/login", json={"username": "alice", "password": PW}).json()["token"]
    assert c.get("/api/me").status_code == 401  # signed-in-only endpoint without a token
    assert c.get("/api/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401  # never a silent guest
    assert c.post("/api/auth/logout", headers={"Authorization": f"Bearer {tok2}"}).status_code == 204
    assert c.get("/api/me", headers={"Authorization": f"Bearer {tok2}"}).status_code == 401


def test_profile_update_validation_and_privacy_defaults(c):
    h = register(c)
    r = c.patch("/api/me", json={"age_range": "46-60", "goals": "regain shoulder movement", "preferences": {"audio_feedback": True}}, headers=h)
    assert r.status_code == 200 and r.json()["age_range"] == "46-60" and r.json()["preferences"] == {"audio_feedback": True}
    assert c.patch("/api/me", json={"age_range": "forty"}, headers=h).status_code == 422
    assert c.patch("/api/me", json={"preferences": {"store_video": True}}, headers=h).status_code == 422  # not an allowed setting
    assert "password" not in str(r.json()).lower()


# ---- sessions, live persistence, recommendation -------------------------------------------------

def test_stream_saves_reps_and_complete_returns_a_recommendation(c):
    h = register(c)
    s = new_session(c, h)
    reps = stream(c, s, 6)
    assert len(reps) >= 6 and all(r["label"] == "acceptable" for r in reps)
    with SessionLocal() as db:
        saved = db.scalars(select(Repetition).where(Repetition.session_id == s["id"])).all()
        assert len(saved) == len(reps) and all(r.counted and r.reliable for r in saved)
    done = complete(c, s, h).json()
    assert done["saved_to_history"] and done["history_used"] and done["session"]["ended_at"]
    rec = done["recommendation"]
    assert rec["classification"] == "good" and rec["action"] == "maintain" and rec["next_level"] == 1
    assert "not a clinical decision" in rec["safety_note"]


def test_two_good_sessions_raise_the_recommended_level_by_one(c):
    h = register(c)
    _, first = play(c, h, 1)
    assert first.json()["recommendation"]["action"] == "maintain"
    _, second = play(c, h, 1)
    rec = second.json()["recommendation"]
    assert rec["action"] == "increase" and rec["next_level"] == 2 and rec["target_reps"] == 8
    st = c.get("/api/adaptation/state", params={"exercise_id": "elbow_flexion"}, headers=h).json()
    assert st["recommended_level"] == 2 and st["source"] == "history" and st["last_action"] == "increase"
    # the first session at the new level never raises it again straight away
    _, third = play(c, h, 2)
    assert third.json()["recommendation"]["next_level"] == 2


def test_poor_sessions_lower_the_level_only_after_confirmation(c):
    h = register(c)
    play(c, h, 1)
    play(c, h, 1)  # -> recommended level 2
    _, p1 = play(c, h, 2, depth=0.5)  # shallow reps
    assert p1.json()["recommendation"]["next_level"] == 2
    _, p2 = play(c, h, 2, depth=0.5)
    rec = p2.json()["recommendation"]
    assert rec["next_level"] == 1 and rec["action"] in ("decrease", "pause")


def test_too_little_data_never_raises_the_level(c):
    h = register(c)
    play(c, h, 1)
    s = new_session(c, h)
    stream(c, s, 2)  # only 2 repetitions
    rec = complete(c, s, h).json()["recommendation"]
    assert rec["classification"] == "insufficient" and rec["next_level"] == 1


def test_reset_returns_to_the_safe_default_level(c):
    h = register(c)
    play(c, h, 1)
    play(c, h, 1)
    assert c.get("/api/adaptation/state", params={"exercise_id": "elbow_flexion"}, headers=h).json()["recommended_level"] == 2
    r = c.post("/api/adaptation/reset", json={"exercise_id": "elbow_flexion"}, headers=h)
    assert r.json()["action"] == "reset" and r.json()["next_level"] == 1
    assert c.get("/api/adaptation/state", params={"exercise_id": "elbow_flexion"}, headers=h).json()["recommended_level"] == 1
    assert c.post("/api/adaptation/reset", json={"exercise_id": "elbow_flexion"}).status_code == 401


def test_demo_and_guest_sessions_never_feed_history_or_analytics(c):
    h = register(c)
    _, demo = play(c, h, 1, demo=True)
    _, demo2 = play(c, h, 1, demo=True)
    assert demo.json()["saved_to_history"] is False and demo2.json()["recommendation"]["action"] == "maintain"
    assert c.get("/api/adaptation/state", params={"exercise_id": "elbow_flexion"}, headers=h).json()["source"] == "default"
    assert c.get("/api/analytics/summary", headers=h).json()["total_sessions"] == 0
    assert c.get("/api/analytics/summary", params={"include_demo": True}, headers=h).json()["total_sessions"] == 2
    assert c.get("/api/sessions", headers=h).json() == []
    g = new_session(c)  # guest
    stream(c, g, 6)
    out = complete(c, g).json()
    assert out["history_used"] is False and c.get("/api/sessions").json() == []
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AdaptiveDecision)) == 0


def test_ownership_and_lifecycle_rules(c):
    a, b = register(c, "alice"), register(c, "bobby")
    s = new_session(c, a)
    assert c.get(f"/api/sessions/{s['id']}", headers=b).status_code == 404
    assert c.get(f"/api/sessions/{s['id']}").status_code == 404
    assert c.post(f"/api/sessions/{s['id']}/complete", headers=b).status_code == 404
    rep = {"index": 1, "label": "acceptable", "score": 0.9, "reliable": True, "counted": True, "features": {"peak_progress": 0.9}}
    assert c.post(f"/api/sessions/{s['id']}/repetitions", json=[rep], headers=b).status_code == 404
    assert c.post(f"/api/sessions/{s['id']}/repetitions", json=[rep], headers=a).status_code == 201
    assert c.post(f"/api/sessions/{s['id']}/repetitions", json=[rep], headers=a).status_code == 409  # duplicate index
    assert complete(c, s, a).status_code == 200
    assert complete(c, s, a).status_code == 409
    assert c.post(f"/api/sessions/{s['id']}/repetitions", json=[{**rep, "index": 2}], headers=a).status_code == 409
    assert c.post("/api/sessions", json={"exercise_id": "nope"}).status_code == 404
    assert c.post("/api/sessions", json={"exercise_id": "elbow_flexion", "difficulty": 4}).status_code == 422
    assert c.post(f"/api/sessions/{s['id']}/repetitions", json=[{**rep, "score": 7}], headers=a).status_code in (409, 422)


def test_live_stream_requires_the_session_key(c):
    h = register(c)
    s = new_session(c, h)
    for bad in ({"key": "wrong"}, {"level": 2}):
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect(f"/api/ws/analysis?exercise_id=elbow_flexion&difficulty={bad.get('level', 1)}"
                                     f"&session_id={s['id']}&key={bad.get('key', s['ws_key'])}") as ws:
                ws.receive_json()
        assert e.value.code == 4403
    complete(c, s, h)
    with pytest.raises(WebSocketDisconnect) as e:  # a finished session cannot receive more repetitions
        with c.websocket_connect(f"/api/ws/analysis?exercise_id=elbow_flexion&difficulty=1&session_id={s['id']}&key={s['ws_key']}") as ws:
            ws.receive_json()
    assert e.value.code == 4403


def test_stateless_recommend_endpoint_and_validation(c):
    rep = {"label": "acceptable", "score": 0.95, "reliable": True, "counted": True, "peak_progress": 0.9}
    body = {"exercise_id": "elbow_flexion", "current_level": 1, "reps": [rep] * 6,
            "history": [{"level": 1, "classification": "good", "action": "maintain"}]}
    r = c.post("/api/adaptation/recommend", json=body)
    assert r.status_code == 200 and r.json()["action"] == "increase" and r.json()["next_level"] == 2
    assert c.post("/api/adaptation/recommend", json={**body, "exercise_id": "nope"}).status_code == 404
    assert c.post("/api/adaptation/recommend", json={**body, "current_level": 5}).status_code == 422
    assert c.post("/api/adaptation/recommend", json={**body, "current_level": 0}).status_code == 422
    assert c.post("/api/adaptation/recommend", json={**body, "reps": [{**rep, "score": 3}]}).status_code == 422


def test_analytics_reflect_only_saved_real_sessions(c):
    h = register(c)
    play(c, h, 1)
    play(c, h, 1)
    s = c.get("/api/analytics/summary", headers=h).json()
    assert s["total_sessions"] == 2 and s["completed_repetitions"] >= 12 and s["average_quality_score"] > 0.9
    assert "not validated medical outcomes" in s["note"]
    p = c.get("/api/analytics/progress", params={"exercise_id": "elbow_flexion"}, headers=h).json()["points"]
    assert [pt["action"] for pt in p] == ["maintain", "increase"] and p[1]["next_level"] == 2
    assert c.get("/api/analytics/summary").status_code == 401


def test_deleting_the_account_removes_all_stored_data(c):
    h = register(c)
    play(c, h, 1)
    play(c, h, 1)
    assert c.delete("/api/me", headers=h).status_code == 204
    with SessionLocal() as db:
        for model in (User, ExerciseSession, Repetition, AdaptiveDecision, AuthToken):
            assert db.scalar(select(func.count()).select_from(model)) == 0, model.__name__
    assert c.get("/api/me", headers=h).status_code == 401
