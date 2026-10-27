from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DISCLAIMER, settings
from app.database.db import ExerciseSession, get_db
from app.exercises.library import Exercise, get_exercise, load_exercises

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
