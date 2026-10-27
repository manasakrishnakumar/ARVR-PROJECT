import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user_optional
from app.database.db import AdaptiveDecision, ExerciseSession, User, get_db
from app.exercises.library import get_exercise
from app.personalization.controller import Recommendation, recommend
from app.services.adaptive_service import (MAX_REPS_PER_SESSION, adaptive_config, add_repetition, history_for,
                                           rep_observations)

router = APIRouter(prefix="/api")


class SessionCreate(BaseModel):
    exercise_id: str
    is_demo: bool = False
    difficulty: int = Field(default=1, ge=1, le=5)


class SessionOut(BaseModel):
    id: str
    exercise_id: str
    is_demo: bool
    difficulty: int
    started_at: datetime
    ended_at: datetime | None
    summary: dict
    model_config = {"from_attributes": True}


class SessionCreated(SessionOut):
    ws_key: str  # per-session secret for the live stream; shown only here


class RepIn(BaseModel):
    index: int = Field(ge=1, le=MAX_REPS_PER_SESSION)
    label: str = Field(max_length=64)
    score: float | None = Field(default=None, ge=0, le=1)
    reliable: bool = True
    counted: bool = False
    features: dict[str, float] = Field(default_factory=dict, max_length=60)


class CompleteOut(BaseModel):
    session: SessionOut
    recommendation: Recommendation
    history_used: bool  # false for guests and demo sessions: judged on this session alone
    saved_to_history: bool


def owned_session(db: Session, session_id: str, user: User | None) -> ExerciseSession:
    """Guest sessions are reachable by their unguessable id; signed-in users' sessions only by their owner."""
    s = db.get(ExerciseSession, session_id)
    if s is None or (s.user_id is not None and (user is None or user.id != s.user_id)):
        raise HTTPException(404, "Session not found")
    return s


@router.post("/sessions", response_model=SessionCreated, status_code=201)
def create_session(body: SessionCreate, user: User | None = Depends(current_user_optional),
                   db: Session = Depends(get_db)) -> SessionCreated:
    ex = get_exercise(body.exercise_id)
    if ex is None:
        raise HTTPException(404, f"Unknown exercise '{body.exercise_id}'")
    if str(body.difficulty) not in ex.difficulty_levels:
        raise HTTPException(422, f"Level {body.difficulty} is not defined for {ex.id}")
    s = ExerciseSession(user_id=user.id if user else None, exercise_id=ex.id, is_demo=body.is_demo,
                        difficulty=body.difficulty, ws_key=secrets.token_urlsafe(24))
    db.add(s)
    db.commit()
    return SessionCreated(**SessionOut.model_validate(s).model_dump(), ws_key=s.ws_key)  # type: ignore[arg-type]


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(exercise_id: str | None = None, include_demo: bool = False, limit: int = Query(50, ge=1, le=200),
                  user: User | None = Depends(current_user_optional), db: Session = Depends(get_db)):
    """Signed-in users see their own sessions. Guest sessions are not listable (there is no account to list them under)."""
    if user is None:
        return []
    q = select(ExerciseSession).where(ExerciseSession.user_id == user.id)
    if exercise_id:
        q = q.where(ExerciseSession.exercise_id == exercise_id)
    if not include_demo:
        q = q.where(ExerciseSession.is_demo.is_(False))
    return list(db.scalars(q.order_by(ExerciseSession.started_at.desc()).limit(limit)))


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str, user: User | None = Depends(current_user_optional), db: Session = Depends(get_db)):
    return owned_session(db, session_id, user)


@router.post("/sessions/{session_id}/repetitions", status_code=201)
def add_repetitions(session_id: str, reps: list[RepIn] = Body(max_length=MAX_REPS_PER_SESSION),
                    user: User | None = Depends(current_user_optional), db: Session = Depends(get_db)) -> dict:
    s = owned_session(db, session_id, user)
    if s.ended_at is not None:
        raise HTTPException(409, "Session already completed")
    existing = {r.index for r in s.repetitions}
    if len(existing) + len(reps) > MAX_REPS_PER_SESSION:
        raise HTTPException(422, f"At most {MAX_REPS_PER_SESSION} repetitions per session")
    if any(r.index in existing for r in reps) or len({r.index for r in reps}) != len(reps):
        raise HTTPException(409, "Duplicate repetition index")
    for r in reps:
        add_repetition(db, s, r.index, r.label, r.score, r.reliable, r.counted, r.features, commit=False)
    db.commit()
    return {"added": len(reps)}


@router.post("/sessions/{session_id}/complete", response_model=CompleteOut)
def complete_session(session_id: str, user: User | None = Depends(current_user_optional),
                     db: Session = Depends(get_db)) -> CompleteOut:
    s = owned_session(db, session_id, user)
    if s.ended_at is not None:
        raise HTTPException(409, "Session already completed")
    ex = get_exercise(s.exercise_id)
    assert ex is not None
    persistent = s.user_id is not None and not s.is_demo
    history = history_for(db, s.user_id, s.exercise_id) if persistent else []  # type: ignore[arg-type]
    rec = recommend(adaptive_config(), ex.difficulty_levels, s.difficulty, rep_observations(s), history)
    s.ended_at = datetime.now(timezone.utc)
    s.summary = {"metrics": rec.metrics.model_dump(), "classification": rec.classification, "action": rec.action,
                 "level": s.difficulty, "next_level": rec.next_level}
    if persistent:
        db.add(AdaptiveDecision(user_id=s.user_id, exercise_id=s.exercise_id, session_id=s.id, from_level=s.difficulty,
                                to_level=rec.next_level, action=rec.action, classification=rec.classification,
                                reasons=rec.reasons, metrics=rec.metrics.model_dump()))
    db.commit()
    return CompleteOut(session=SessionOut.model_validate(s), recommendation=rec, history_used=persistent,
                       saved_to_history=persistent)
