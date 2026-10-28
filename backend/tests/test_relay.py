import json
import os
import tempfile

os.environ.setdefault("ARVR_DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/relay.db")

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api import relay
from app.main import app


def frame(**extra):
    return json.dumps({"lm": [0.5] * 132, "angle": 90.0, "phase": "rest", **extra})


@pytest.fixture
def c():
    relay.rooms.clear()
    with TestClient(app) as client:
        yield client


def join(c, room, role):
    return c.websocket_connect(f"/api/ws/relay/{room}?role={role}")


def test_frames_reach_subscribers_unchanged_and_nothing_is_stored(c):
    with join(c, "ROOM01", "subscriber") as sub, join(c, "ROOM01", "publisher") as pub:
        assert sub.receive_json()["role"] == "subscriber" and pub.receive_json()["role"] == "publisher"
        pub.send_text(frame(counted_reps=3))
        got = json.loads(sub.receive_text())
        assert got["counted_reps"] == 3 and len(got["lm"]) == 132 and got["angle"] == 90.0
    assert relay.rooms == {}  # rooms vanish when the last client leaves


def test_rooms_are_isolated(c):
    with join(c, "AAAAAA", "subscriber") as a, join(c, "BBBBBB", "publisher") as pub, join(c, "AAAAAA", "publisher") as pa:
        a.receive_json(); pub.receive_json(); pa.receive_json()
        pub.send_text(frame(phase="room-b"))
        pa.send_text(frame(phase="room-a"))
        assert json.loads(a.receive_text())["phase"] == "room-a"  # never room B's frame


def test_invalid_frames_are_rejected_without_closing_the_stream(c):
    with join(c, "ROOM02", "publisher") as pub, join(c, "ROOM02", "subscriber") as sub:
        pub.receive_json(); sub.receive_json()
        for bad in ("not json", json.dumps({"lm": [0.1] * 5}), json.dumps({"lm": ["x"] * 132}), json.dumps([1, 2]),
                    json.dumps({"lm": [True] * 132}), "x" * 9000, json.dumps({"lm": [1e999] * 132})):
            pub.send_text(bad)
            assert pub.receive_json()["type"] == "error"
        pub.send_text(frame())  # still works afterwards
        assert json.loads(sub.receive_text())["angle"] == 90.0


@pytest.mark.parametrize("room,role", [("abc", "publisher"), ("lowercase1", "publisher"), ("ROOM-01", "subscriber"), ("TOOLONGROOMCODE1", "subscriber"), ("ROOM03", "spy")])
def test_bad_room_codes_and_roles_are_closed(c, room, role):
    with pytest.raises(WebSocketDisconnect) as e:
        with join(c, room, role) as ws:
            ws.receive_json()
    assert e.value.code == 4422


def test_second_publisher_and_too_many_subscribers_are_refused(c):
    with join(c, "ROOM04", "publisher") as p1:
        p1.receive_json()
        with pytest.raises(WebSocketDisconnect) as e:
            with join(c, "ROOM04", "publisher") as p2:
                p2.receive_json()
        assert e.value.code == 4409
        subs = [join(c, "ROOM04", "subscriber").__enter__() for _ in range(relay.MAX_SUBSCRIBERS)]
        with pytest.raises(WebSocketDisconnect) as e2:
            with join(c, "ROOM04", "subscriber") as extra:
                extra.receive_json()
        assert e2.value.code == 4429
        for s in subs:
            s.__exit__(None, None, None)


def test_room_limit(c, monkeypatch):
    monkeypatch.setattr(relay, "MAX_ROOMS", 2)
    with join(c, "ROOMAA", "subscriber") as a, join(c, "ROOMBB", "subscriber") as b:
        a.receive_json(); b.receive_json()
        with pytest.raises(WebSocketDisconnect) as e:
            with join(c, "ROOMCC", "subscriber") as x:
                x.receive_json()
        assert e.value.code == 4429


def test_a_subscriber_leaving_does_not_break_the_publisher(c):
    with join(c, "ROOM05", "publisher") as pub:
        pub.receive_json()
        with join(c, "ROOM05", "subscriber") as s:
            s.receive_json()
        pub.send_text(frame())  # subscriber is gone: no error
        with join(c, "ROOM05", "subscriber") as s2:
            s2.receive_json()
            pub.send_text(frame(phase="again"))
            assert json.loads(s2.receive_text())["phase"] == "again"
