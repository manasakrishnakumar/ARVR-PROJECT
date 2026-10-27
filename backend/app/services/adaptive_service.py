"""Glue between the database and the adaptive controller (the controller itself stays database-free)."""
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.db import AdaptiveDecision, ExerciseSession, Repetition
from app.personalization.controller import AdaptiveConfig, HistoryItem, RepObs

MAX_REPS_PER_SESSION = 500


@lru_cache
def adaptive_config() -> AdaptiveConfig:
    return AdaptiveConfig.load()


def history_for(db: Session, user_id: str, exercise_id: str, limit: int = 20) -> list[HistoryItem]:
    rows = db.scalars(select(AdaptiveDecision).where(AdaptiveDecision.user_id == user_id,
                                                     AdaptiveDecision.exercise_id == exercise_id)
                      .order_by(AdaptiveDecision.created_at.desc()).limit(limit)).all()
    return [HistoryItem(level=r.from_level, classification=r.classification, action=r.action) for r in rows]  # type: ignore[arg-type]


def latest_decision(db: Session, user_id: str, exercise_id: str) -> AdaptiveDecision | None:
    return db.scalar(select(AdaptiveDecision).where(AdaptiveDecision.user_id == user_id,
                                                    AdaptiveDecision.exercise_id == exercise_id)
                     .order_by(AdaptiveDecision.created_at.desc()).limit(1))


def rep_observations(session: ExerciseSession) -> list[RepObs]:
    return [RepObs(label=r.quality_label or "insufficient_data", score=r.quality_score, reliable=bool(r.reliable),
                   counted=bool(r.counted), peak_progress=float((r.features or {}).get("peak_progress", 0.0)))
            for r in session.repetitions]


def add_repetition(db: Session, session: ExerciseSession, index: int, label: str, score: float | None, reliable: bool,
                   counted: bool, features: dict, commit: bool = True) -> Repetition:
    rep = Repetition(session_id=session.id, index=index, quality_label=label, quality_score=score, reliable=reliable,
                     counted=counted, features=features, range_of_motion_deg=features.get("rom_deg"),
                     duration_s=features.get("duration_s"))
    db.add(rep)
    if commit:
        db.commit()
    return rep
