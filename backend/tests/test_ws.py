import os
import tempfile

os.environ["ARVR_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/ws.db"

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.synthetic.sequences import make_sequence


def test_stream_counts_reps_and_emits_feedback():
    seq = make_sequence(160, 50, 2, period_s=3, fps=15)
    reps, last_state = [], None
    with TestClient(app) as c, c.websocket_connect("/api/ws/analysis?exercise_id=elbow_flexion&difficulty=1") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["target_reps"] == 5
        for t, a in seq:
            ws.send_json({"t": t, "angle": a})
            msg = ws.receive_json()
            assert msg["type"] == "state"
            # a "rep" message follows the state message on the frame a repetition finishes
            if last_state is not None and msg["counted_reps"] > last_state["counted_reps"]:
                rep = ws.receive_json()
                assert rep["type"] == "rep"
                reps.append(rep)
            last_state = msg
    assert last_state["counted_reps"] == 2
    assert [r["label"] for r in reps] == ["acceptable", "acceptable"]
    assert all(r["feedback"] for r in reps)


def test_stream_rejects_bad_input_and_keeps_going():
    with TestClient(app) as c, c.websocket_connect("/api/ws/analysis?exercise_id=knee_flexion") as ws:
        ws.receive_json()
        ws.send_json({"t": 1.0, "angle": 999})
        assert ws.receive_json()["type"] == "error"
        ws.send_json({"t": 2.0, "angle": None})
        assert ws.receive_json()["type"] == "state"
        ws.send_json({"t": 1.5, "angle": 100})  # time going backwards
        assert ws.receive_json()["type"] == "error"


def test_stream_unknown_exercise_and_difficulty_closed():
    with TestClient(app) as c:
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect("/api/ws/analysis?exercise_id=nope") as ws:
                ws.receive_json()
        assert e.value.code == 4404
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect("/api/ws/analysis?exercise_id=knee_flexion&difficulty=9") as ws:
                ws.receive_json()
        assert e.value.code == 4422
