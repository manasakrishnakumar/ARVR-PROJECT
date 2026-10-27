import secrets

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.core.config import DISCLAIMER, settings
from app.database.db import ExerciseSession, SessionLocal
from app.exercises.library import Exercise, get_exercise, load_exercises
from app.ml.inference import model_status
from app.services.adaptive_service import MAX_REPS_PER_SESSION, add_repetition
from app.services.analysis import RepResult, StreamAnalyzer, analyze_series

router = APIRouter(prefix="/api")


class Health(BaseModel):
    status: str
    version: str
    disclaimer: str


class AngleSample(BaseModel):
    t: float = Field(ge=0, description="seconds from start of series")
    angle: float | None = Field(default=None, ge=0, le=360, description="null = landmark missing/unreliable")


class EvaluateRequest(BaseModel):
    exercise_id: str
    difficulty: int = Field(default=1, ge=1, le=5)
    samples: list[AngleSample] = Field(min_length=2, max_length=20000)


class RepOut(BaseModel):
    index: int
    t_start: float
    t_end: float
    counted: bool
    label: str
    score: float | None
    reliable: bool
    explanation: str
    feedback: str
    features: dict[str, float]


class EvaluateResponse(BaseModel):
    exercise_id: str
    difficulty: int
    counted_reps: int
    attempts: list[RepOut]
    final_phase: str
    method: str = "rule_based"
    disclaimer: str = DISCLAIMER


def _rep_out(r: RepResult) -> RepOut:
    return RepOut(
        index=r.repetition.index, t_start=r.repetition.t_start, t_end=r.repetition.t_end, counted=r.counted,
        label=r.assessment.label, score=r.assessment.score, reliable=r.assessment.reliable,
        explanation=r.assessment.explanation, feedback=r.assessment.feedback, features=r.assessment.features,
    )


def _persist_rep(session_id: str, rep: RepOut) -> None:
    """Store a finished repetition against the session the stream is bound to (own DB session: the socket is long-lived)."""
    with SessionLocal() as db:
        s = db.get(ExerciseSession, session_id)
        if s is not None and s.ended_at is None and len(s.repetitions) < MAX_REPS_PER_SESSION:
            add_repetition(db, s, rep.index, rep.label, rep.score, rep.reliable, rep.counted, rep.features)


@router.websocket("/ws/analysis")
async def analysis_ws(ws: WebSocket, exercise_id: str, difficulty: int = 1, session_id: str | None = None,
                      key: str | None = None) -> None:
    """Live stream: client sends {"t": seconds, "angle": deg|null}; server replies with state per frame
    and a "rep" message whenever a repetition finishes. Pose estimation stays in the browser.

    With session_id + key (returned when the session was created) finished repetitions are also saved to that session."""
    await ws.accept()
    ex = get_exercise(exercise_id)
    try:
        if ex is None:
            await ws.close(code=4404, reason="unknown exercise")
            return
        if session_id is not None:
            with SessionLocal() as db:
                s = db.get(ExerciseSession, session_id)
                ok = (s is not None and s.ws_key is not None and key is not None and secrets.compare_digest(s.ws_key, key)
                      and s.exercise_id == ex.id and s.difficulty == difficulty and s.ended_at is None)
            if not ok:
                await ws.close(code=4403, reason="session not found, closed, or key/exercise/level mismatch")
                return
        try:
            sa = StreamAnalyzer(ex, difficulty)
        except ValueError as e:
            await ws.close(code=4422, reason=str(e)[:100])
            return
        await ws.send_json({"type": "hello", "exercise_id": ex.id, "difficulty": difficulty,
                            "target_reps": sa.level["target_reps"], "disclaimer": DISCLAIMER,
                            "saving": session_id is not None})
        last_t = -1.0
        while True:
            msg = await ws.receive_json()
            try:
                t = float(msg["t"])
                angle = msg.get("angle")
                angle = None if angle is None else float(angle)
                if t < last_t or (angle is not None and not 0 <= angle <= 360):
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                await ws.send_json({"type": "error", "detail": "expected ordered {t, angle} with angle in 0..360 or null"})
                continue
            last_t = t
            u = sa.push(t, angle)
            await ws.send_json({"type": "state", "phase": u.phase, "counted_reps": u.counted_reps,
                                "angle": u.angle, "progress": u.progress})
            if u.rep is not None:
                rep = _rep_out(u.rep)
                if session_id is not None:
                    _persist_rep(session_id, rep)
                await ws.send_json({"type": "rep", **rep.model_dump()})
    except WebSocketDisconnect:
        return


@router.post("/assessment/evaluate", response_model=EvaluateResponse)
def evaluate(body: EvaluateRequest) -> EvaluateResponse:
    ex = get_exercise(body.exercise_id)
    if ex is None:
        raise HTTPException(404, f"Unknown exercise '{body.exercise_id}'")
    times = [s.t for s in body.samples]
    if any(b < a for a, b in zip(times, times[1:])):
        raise HTTPException(422, "samples must be ordered by time")
    try:
        res = analyze_series(ex, body.difficulty, [(s.t, s.angle) for s in body.samples])
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    attempts = [_rep_out(r) for r in res.attempts]
    return EvaluateResponse(exercise_id=ex.id, difficulty=body.difficulty, counted_reps=res.counted_reps,
                            attempts=attempts, final_phase=res.final_phase)


@router.get("/models/status")
def models_status() -> dict:
    return model_status(settings.artifacts_dir)


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", version=settings.version, disclaimer=DISCLAIMER)


@router.get("/exercises", response_model=list[Exercise])
def list_exercises() -> list[Exercise]:
    return list(load_exercises().values())


@router.get("/exercises/{exercise_id}", response_model=Exercise)
def exercise_detail(exercise_id: str) -> Exercise:
    ex = get_exercise(exercise_id)
    if ex is None:
        raise HTTPException(404, f"Unknown exercise '{exercise_id}'")
    return ex
