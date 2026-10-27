from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import DISCLAIMER
from app.database.db import AdaptiveDecision, ExerciseSession, User, get_db

router = APIRouter(prefix="/api/analytics")
LABEL_NOTE = "Experimental system metrics from a research prototype, not validated medical outcomes."


def _sessions(db: Session, user: User, exercise_id: str | None, include_demo: bool) -> list[ExerciseSession]:
    q = select(ExerciseSession).where(ExerciseSession.user_id == user.id, ExerciseSession.ended_at.is_not(None))
    if exercise_id:
        q = q.where(ExerciseSession.exercise_id == exercise_id)
    if not include_demo:
        q = q.where(ExerciseSession.is_demo.is_(False))  # synthetic demo sessions never appear in real analytics
    return list(db.scalars(q.order_by(ExerciseSession.started_at)))


@router.get("/summary")
def summary(exercise_id: str | None = None, include_demo: bool = False, user: User = Depends(current_user),
            db: Session = Depends(get_db)) -> dict:
    sessions = _sessions(db, user, exercise_id, include_demo)
    quality = [s.summary["metrics"]["quality"] for s in sessions if (s.summary.get("metrics") or {}).get("quality") is not None]
    errors: Counter = Counter()
    for s in sessions:
        errors.update(r.quality_label for r in s.repetitions if r.reliable and r.quality_label and r.quality_label != "acceptable")
    return {
        "total_sessions": len(sessions),
        "demo_sessions_included": include_demo and any(s.is_demo for s in sessions),
        "completed_repetitions": sum(r.counted for s in sessions for r in s.repetitions),
        "average_quality_score": (sum(quality) / len(quality)) if quality else None,
        "total_duration_s": sum((s.ended_at - s.started_at).total_seconds() for s in sessions if s.ended_at),
        "error_categories": dict(errors),
        "sessions_by_exercise": dict(Counter(s.exercise_id for s in sessions)),
        "note": LABEL_NOTE, "disclaimer": DISCLAIMER,
    }


@router.get("/progress")
def progress(exercise_id: str | None = None, include_demo: bool = False, user: User = Depends(current_user),
             db: Session = Depends(get_db)) -> dict:
    sessions = _sessions(db, user, exercise_id, include_demo)
    decisions = {d.session_id: d for d in db.scalars(select(AdaptiveDecision).where(AdaptiveDecision.user_id == user.id))}
    points = []
    for s in sessions:
        m = (s.summary or {}).get("metrics") or {}
        d = decisions.get(s.id)
        points.append({"session_id": s.id, "exercise_id": s.exercise_id, "started_at": s.started_at, "is_demo": s.is_demo,
                       "level": s.difficulty, "counted_reps": m.get("counted_reps"), "target_reps": m.get("target_reps"),
                       "quality": m.get("quality"), "error_rate": m.get("error_rate"),
                       "classification": (s.summary or {}).get("classification"),
                       "action": d.action if d else None, "next_level": d.to_level if d else None})
    return {"points": points, "note": LABEL_NOTE}
