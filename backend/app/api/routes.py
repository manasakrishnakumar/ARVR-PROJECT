from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DISCLAIMER, settings
from app.database.db import ExerciseSession, get_db
from app.exercises.library import Exercise, get_exercise, load_exercises
from app.services.analysis import analyze_series

router = APIRouter(prefix="/api")


class Health(BaseModel):
    status: str
    version: str
    disclaimer: str


class SessionCreate(BaseModel):
    exercise_id: str
    user_id: str | None = None
    is_demo: bool = False
    difficulty: int = Field(default=1, ge=1, le=5)


class SessionOut(BaseModel):
    id: str
    exercise_id: str
    user_id: str | None
    is_demo: bool
    difficulty: int
    model_config = {"from_attributes": True}


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
    attempts = [
        RepOut(index=r.repetition.index, t_start=r.repetition.t_start, t_end=r.repetition.t_end, counted=r.counted,
               label=r.assessment.label, score=r.assessment.score, reliable=r.assessment.reliable,
               explanation=r.assessment.explanation, feedback=r.assessment.feedback, features=r.assessment.features)
        for r in res.attempts
    ]
    return EvaluateResponse(exercise_id=ex.id, difficulty=body.difficulty, counted_reps=res.counted_reps,
                            attempts=attempts, final_phase=res.final_phase)


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


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db)) -> ExerciseSession:
    if get_exercise(body.exercise_id) is None:
        raise HTTPException(404, f"Unknown exercise '{body.exercise_id}'")
    s = ExerciseSession(**body.model_dump())
    db.add(s)
    db.commit()
    return s


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)) -> list[ExerciseSession]:
    return list(db.scalars(select(ExerciseSession).order_by(ExerciseSession.started_at.desc())))


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: Session = Depends(get_db)) -> ExerciseSession:
    s = db.get(ExerciseSession, session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    return s
