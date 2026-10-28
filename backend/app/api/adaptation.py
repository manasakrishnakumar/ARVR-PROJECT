from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_user, current_user_optional
from app.database.db import AdaptiveDecision, User, get_db
from app.exercises.library import get_exercise
from app.personalization.controller import HistoryItem, RepObs, Recommendation, recommend, reset_to_default
from app.services.adaptive_service import adaptive_config, latest_decision

router = APIRouter(prefix="/api/adaptation")


class RecommendIn(BaseModel):
    exercise_id: str
    current_level: int = Field(ge=1, le=5)
    reps: list[RepObs] = Field(max_length=500)
    history: list[HistoryItem] = Field(default_factory=list, max_length=50)  # newest first
    pain: int | None = Field(default=None, ge=0, le=10)


class ExerciseRef(BaseModel):
    exercise_id: str


class StateOut(BaseModel):
    exercise_id: str
    recommended_level: int
    source: str  # "history" (from your last session) or "default"
    last_action: str | None = None
    last_reasons: list[str] = []
    last_at: datetime | None = None


def _levels(exercise_id: str) -> dict:
    ex = get_exercise(exercise_id)
    if ex is None:
        raise HTTPException(404, f"Unknown exercise '{exercise_id}'")
    return ex.difficulty_levels


@router.post("/recommend", response_model=Recommendation)
def recommend_stateless(body: RecommendIn) -> Recommendation:
    """Pure policy evaluation: no database, no account. Useful for experiments and for clients that keep their own history."""
    try:
        return recommend(adaptive_config(), _levels(body.exercise_id), body.current_level, body.reps, body.history, body.pain)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.get("/state", response_model=StateOut)
def state(exercise_id: str, user: User | None = Depends(current_user_optional), db: Session = Depends(get_db)) -> StateOut:
    levels = _levels(exercise_id)
    default = min(max(adaptive_config().default_level, min(int(k) for k in levels)), max(int(k) for k in levels))
    last = latest_decision(db, user.id, exercise_id) if user else None
    if last is None:
        return StateOut(exercise_id=exercise_id, recommended_level=default, source="default")
    return StateOut(exercise_id=exercise_id, recommended_level=last.to_level, source="history", last_action=last.action,
                    last_reasons=list(last.reasons or []), last_at=last.created_at)


@router.post("/reset", response_model=Recommendation)
def reset(body: ExerciseRef, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Recommendation:
    """Reset this exercise to the safe default level (recorded as a decision so the history stays explainable)."""
    rec = reset_to_default(adaptive_config(), _levels(body.exercise_id))
    db.add(AdaptiveDecision(user_id=user.id, exercise_id=body.exercise_id, session_id=None, from_level=rec.current_level,
                            to_level=rec.next_level, action="reset", classification="insufficient", reasons=rec.reasons,
                            metrics={}))
    db.commit()
    return rec
