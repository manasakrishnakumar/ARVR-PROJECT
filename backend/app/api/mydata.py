"""The signed-in user's own data: full backup and restore (JSON), and a light weekly summary."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database.db import AdaptiveDecision, ExerciseSession, Repetition, User, get_db
from app.exercises.library import get_exercise
from app.services.adaptive_service import MAX_REPS_PER_SESSION

router = APIRouter(prefix="/api")
BACKUP_VERSION = 1
MAX_RESTORE_SESSIONS = 2000


class BackupRep(BaseModel):
    index: int = Field(ge=1, le=MAX_REPS_PER_SESSION)
    label: str | None = Field(default=None, max_length=64)
    score: float | None = Field(default=None, ge=0, le=1)
    counted: bool = False
    reliable: bool = True
    range_of_motion_deg: float | None = None
    duration_s: float | None = None
    features: dict[str, float] = Field(default_factory=dict, max_length=60)


class BackupDecision(BaseModel):
    from_level: int = Field(ge=1, le=5)
    to_level: int = Field(ge=1, le=5)
    action: str = Field(max_length=16)
    classification: str = Field(max_length=16)
    reasons: list[str] = Field(default_factory=list, max_length=20)
    metrics: dict = Field(default_factory=dict)


class BackupSession(BaseModel):
    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    exercise_id: str = Field(max_length=64)
    difficulty: int = Field(ge=1, le=5)
    started_at: datetime
    ended_at: datetime
    summary: dict = Field(default_factory=dict)
    pain: int | None = Field(default=None, ge=0, le=10)
    note: str | None = Field(default=None, max_length=500)
    repetitions: list[BackupRep] = Field(default_factory=list, max_length=MAX_REPS_PER_SESSION)
    decision: BackupDecision | None = None


class Backup(BaseModel):
    version: int
    exported_at: datetime | None = None
    sessions: list[BackupSession] = Field(max_length=MAX_RESTORE_SESSIONS)


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


@router.get("/me/backup", response_model=Backup)
def backup(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Backup:
    """Everything stored about the user's real (non-demo, completed) sessions, as one JSON file they can keep and restore later.
    Contains no password, token or video."""
    rows = db.scalars(select(ExerciseSession).where(ExerciseSession.user_id == user.id, ExerciseSession.ended_at.is_not(None),
                                                    ExerciseSession.is_demo.is_(False)).order_by(ExerciseSession.started_at)).all()
    out = []
    for s in rows:
        d = db.scalar(select(AdaptiveDecision).where(AdaptiveDecision.session_id == s.id))
        out.append(BackupSession(
            id=s.id, exercise_id=s.exercise_id, difficulty=s.difficulty, started_at=_aware(s.started_at), ended_at=_aware(s.ended_at),
            summary=s.summary or {}, pain=s.pain, note=s.note,
            repetitions=[BackupRep(index=r.index, label=r.quality_label, score=r.quality_score, counted=bool(r.counted),
                                   reliable=bool(r.reliable), range_of_motion_deg=r.range_of_motion_deg, duration_s=r.duration_s,
                                   features=r.features or {}) for r in s.repetitions],
            decision=BackupDecision(from_level=d.from_level, to_level=d.to_level, action=d.action, classification=d.classification,
                                    reasons=list(d.reasons or []), metrics=d.metrics or {}) if d else None))
    return Backup(version=BACKUP_VERSION, exported_at=datetime.now(timezone.utc), sessions=out)


@router.post("/me/restore")
def restore(body: Backup, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Adds sessions from a backup. Sessions whose id already exists are skipped, so restoring twice never duplicates anything
    and one account can never overwrite another account's data."""
    if body.version != BACKUP_VERSION:
        raise HTTPException(422, f"Unsupported backup version {body.version}")
    added = skipped = 0
    for s in body.sessions:
        ex = get_exercise(s.exercise_id)
        if ex is None or str(s.difficulty) not in ex.difficulty_levels:
            raise HTTPException(422, f"Session {s.id}: unknown exercise or level")
        if len({r.index for r in s.repetitions}) != len(s.repetitions):
            raise HTTPException(422, f"Session {s.id}: duplicate repetition index")
        if db.get(ExerciseSession, s.id) is not None:
            skipped += 1
            continue
        db.add(ExerciseSession(id=s.id, user_id=user.id, exercise_id=s.exercise_id, is_demo=False, difficulty=s.difficulty,
                               started_at=s.started_at, ended_at=s.ended_at, summary=s.summary, pain=s.pain, note=s.note))
        db.flush()
        for r in s.repetitions:
            db.add(Repetition(session_id=s.id, index=r.index, quality_label=r.label, quality_score=r.score, counted=r.counted,
                              reliable=r.reliable, range_of_motion_deg=r.range_of_motion_deg, duration_s=r.duration_s, features=r.features))
        if s.decision:
            d = s.decision
            db.add(AdaptiveDecision(user_id=user.id, exercise_id=s.exercise_id, session_id=s.id, from_level=d.from_level,
                                    to_level=d.to_level, action=d.action, classification=d.classification, reasons=d.reasons,
                                    metrics=d.metrics, created_at=s.ended_at))
        added += 1
    db.commit()
    return {"added": added, "skipped": skipped}


@router.get("/analytics/weekly")
def weekly(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Light, non-clinical summary: sessions and repetitions in the last 7 days and the current run of consecutive days with a session."""
    now = datetime.now(timezone.utc)
    rows = db.scalars(select(ExerciseSession).where(ExerciseSession.user_id == user.id, ExerciseSession.ended_at.is_not(None),
                                                    ExerciseSession.is_demo.is_(False))).all()
    days = {_aware(s.started_at).date() for s in rows}
    today = now.date()
    cursor = today if today in days else today - timedelta(days=1)  # a streak is still alive until the day has passed
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    week = [s for s in rows if _aware(s.started_at) >= now - timedelta(days=7)]
    reps = sum(((s.summary or {}).get("metrics") or {}).get("counted_reps") or 0 for s in week)
    return {"sessions_last_7_days": len(week), "counted_repetitions_last_7_days": reps, "day_streak": streak,
            "active_days_last_7": len({_aware(s.started_at).date() for s in week}),
            "note": "Activity counts only; they say nothing about recovery or quality."}
