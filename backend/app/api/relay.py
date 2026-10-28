"""Local pose relay: the browser (publisher) forwards landmark numbers to other clients such as the Unity app (subscribers)
that join the same room code. Pose estimation stays in the browser; no video or image ever passes through here.

Frames are forwarded and never stored; rooms live in memory and vanish when the last client leaves. A room code is a
short unguessable-enough token for a single-user local setup, not an account credential: do not expose this server to the internet.
"""
import json
import math
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api")
ROOM_RE = re.compile(r"^[A-Z0-9]{6,12}$")
LANDMARK_VALUES = 33 * 4  # x, y, z, visibility per MediaPipe landmark
MAX_MESSAGE_BYTES = 8192
MAX_ROOMS = 50
MAX_SUBSCRIBERS = 5


class Room:
    def __init__(self) -> None:
        self.publisher: WebSocket | None = None
        self.subscribers: set[WebSocket] = set()


rooms: dict[str, Room] = {}


def valid_frame(text: str) -> bool:
    if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
        return False
    try:
        m = json.loads(text)
    except json.JSONDecodeError:
        return False
    lm = m.get("lm") if isinstance(m, dict) else None
    return (isinstance(lm, list) and len(lm) == LANDMARK_VALUES
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in lm))


@router.websocket("/ws/relay/{room}")
async def relay(ws: WebSocket, room: str, role: str = "subscriber") -> None:
    await ws.accept()
    if role not in ("publisher", "subscriber") or not ROOM_RE.match(room):
        await ws.close(code=4422, reason="role must be publisher or subscriber; room must be 6-12 letters/digits (A-Z, 0-9)")
        return
    r = rooms.get(room)
    if r is None:
        if len(rooms) >= MAX_ROOMS:
            await ws.close(code=4429, reason="too many rooms")
            return
        r = rooms[room] = Room()
    if role == "publisher":
        if r.publisher is not None:
            await ws.close(code=4409, reason="room already has a publisher")
            return
        r.publisher = ws
    else:
        if len(r.subscribers) >= MAX_SUBSCRIBERS:
            await ws.close(code=4429, reason="too many subscribers")
            return
        r.subscribers.add(ws)
    await ws.send_json({"type": "joined", "room": room, "role": role, "subscribers": len(r.subscribers)})
    try:
        while True:
            text = await ws.receive_text()
            if role != "publisher":
                continue  # subscribers only listen
            if not valid_frame(text):
                await ws.send_json({"type": "error", "detail": f"frame must be a JSON object with 'lm': {LANDMARK_VALUES} finite numbers, max {MAX_MESSAGE_BYTES} bytes"})
                continue
            for sub in list(r.subscribers):
                try:
                    await sub.send_text(text)
                except Exception:  # a slow or closed subscriber must not stop the stream
                    r.subscribers.discard(sub)
    except WebSocketDisconnect:
        pass
    finally:
        if role == "publisher" and r.publisher is ws:
            r.publisher = None
        r.subscribers.discard(ws)
        if r.publisher is None and not r.subscribers:
            rooms.pop(room, None)
