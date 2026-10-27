import csv
import io
import statistics
from collections import Counter
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import DISCLAIMER
from app.database.db import AdaptiveDecision, ExerciseSession, User, get_db

router = APIRouter(prefix="/api/analytics")
LABEL_NOTE = "Experimental system metrics from a research prototype, not validated medical outcomes."


def _bounds(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    lo = datetime.combine(date_from, time.min, tzinfo=timezone.utc) if date_from else None
    hi = datetime.combine(date_to, time.max, tzinfo=timezone.utc) if date_to else None
    return lo, hi


def _sessions(db: Session, user: User, exercise_id: str | None, include_demo: bool,
              date_from: date | None = None, date_to: date | None = None) -> list[ExerciseSession]:
    q = select(ExerciseSession).where(ExerciseSession.user_id == user.id, ExerciseSession.ended_at.is_not(None))
    if exercise_id:
        q = q.where(ExerciseSession.exercise_id == exercise_id)
    if not include_demo:
        q = q.where(ExerciseSession.is_demo.is_(False))  # synthetic demo sessions never appear in real analytics
    lo, hi = _bounds(date_from, date_to)
    if lo:
        q = q.where(ExerciseSession.started_at >= lo)
    if hi:
        q = q.where(ExerciseSession.started_at <= hi)
    return list(db.scalars(q.order_by(ExerciseSession.started_at)))


def _duration(s: ExerciseSession) -> float:
    if s.ended_at is None:
        return 0.0
    a, b = s.started_at, s.ended_at
    a = a if a.tzinfo else a.replace(tzinfo=timezone.utc)
    b = b if b.tzinfo else b.replace(tzinfo=timezone.utc)
    return max(0.0, (b - a).total_seconds())


def _mean_rom(s: ExerciseSession) -> float | None:
    vals = [r.range_of_motion_deg for r in s.repetitions if r.reliable and r.range_of_motion_deg is not None]
    return statistics.fmean(vals) if vals else None


@router.get("/summary")
def summary(exercise_id: str | None = None, include_demo: bool = False, date_from: date | None = Query(None, alias="from"),
            date_to: date | None = Query(None, alias="to"), user: User = Depends(current_user),
            db: Session = Depends(get_db)) -> dict:
    sessions = _sessions(db, user, exercise_id, include_demo, date_from, date_to)
    quality = [s.summary["metrics"]["quality"] for s in sessions if (s.summary.get("metrics") or {}).get("quality") is not None]
    errors: Counter = Counter()
    for s in sessions:
        errors.update(r.quality_label for r in s.repetitions if r.reliable and r.quality_label and r.quality_label != "acceptable")
    return {
        "total_sessions": len(sessions),
        "demo_sessions_included": include_demo and any(s.is_demo for s in sessions),
        "completed_repetitions": sum(r.counted for s in sessions for r in s.repetitions),
        "average_quality_score": (sum(quality) / len(quality)) if quality else None,
        "total_duration_s": sum(_duration(s) for s in sessions),
        "error_categories": dict(errors),
        "sessions_by_exercise": dict(Counter(s.exercise_id for s in sessions)),
        "note": LABEL_NOTE, "disclaimer": DISCLAIMER,
    }


@router.get("/progress")
def progress(exercise_id: str | None = None, include_demo: bool = False, date_from: date | None = Query(None, alias="from"),
             date_to: date | None = Query(None, alias="to"), user: User = Depends(current_user),
             db: Session = Depends(get_db)) -> dict:
    sessions = _sessions(db, user, exercise_id, include_demo, date_from, date_to)
    decisions = {d.session_id: d for d in db.scalars(select(AdaptiveDecision).where(AdaptiveDecision.user_id == user.id))}
    points = []
    for s in sessions:
        m = (s.summary or {}).get("metrics") or {}
        d = decisions.get(s.id)
        points.append({"session_id": s.id, "exercise_id": s.exercise_id, "started_at": s.started_at, "is_demo": s.is_demo,
                       "level": s.difficulty, "counted_reps": m.get("counted_reps"), "target_reps": m.get("target_reps"),
                       "quality": m.get("quality"), "error_rate": m.get("error_rate"), "duration_s": _duration(s),
                       "mean_rom_deg": _mean_rom(s), "classification": (s.summary or {}).get("classification"),
                       "action": d.action if d else None, "next_level": d.to_level if d else None})
    return {"points": points, "note": LABEL_NOTE}


def _csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


@router.get("/export.csv")
def export_csv(kind: str = Query("sessions", pattern="^(sessions|repetitions)$"), exercise_id: str | None = None,
               include_demo: bool = False, date_from: date | None = Query(None, alias="from"),
               date_to: date | None = Query(None, alias="to"), user: User = Depends(current_user),
               db: Session = Depends(get_db)) -> Response:
    """CSV of the signed-in user's own saved data. Experimental system metrics, not validated medical outcomes."""
    sessions = _sessions(db, user, exercise_id, include_demo, date_from, date_to)
    if kind == "sessions":
        body = _csv(["session_id", "started_at_utc", "exercise_id", "is_demo", "level", "counted_reps", "target_reps",
                     "mean_quality_score", "flagged_fraction", "duration_s", "mean_range_of_motion_deg", "classification",
                     "suggested_next_level"],
                    [[s.id, s.started_at.isoformat(), s.exercise_id, s.is_demo, s.difficulty,
                      (s.summary.get("metrics") or {}).get("counted_reps"), (s.summary.get("metrics") or {}).get("target_reps"),
                      (s.summary.get("metrics") or {}).get("quality"), (s.summary.get("metrics") or {}).get("error_rate"),
                      round(_duration(s), 1), _mean_rom(s), s.summary.get("classification"), s.summary.get("next_level")]
                     for s in sessions])
    else:
        body = _csv(["session_id", "exercise_id", "repetition", "label", "score", "counted", "reliable",
                     "range_of_motion_deg", "duration_s"],
                    [[s.id, s.exercise_id, r.index, r.quality_label, r.quality_score, r.counted, r.reliable,
                      r.range_of_motion_deg, r.duration_s] for s in sessions for r in s.repetitions])
    return Response(body, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="arvr-{kind}.csv"'})
