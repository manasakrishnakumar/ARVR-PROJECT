"""Exercise definitions are data (JSON), kept separate from application code.

All numeric targets are ILLUSTRATIVE defaults, not medically prescribed values.
"""
import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.config import settings


class Phase(BaseModel):
    name: str
    description: str


class Exercise(BaseModel):
    id: str
    name: str
    target_joints: list[str]
    landmarks: list[str] = Field(description="MediaPipe landmark names forming the angle A-B-C (B is the vertex)")
    side: str = "left"
    phases: list[Phase]
    start_angle_deg: float
    target_angle_deg: float
    hysteresis_deg: float = 8.0
    min_rep_duration_s: float = 1.0
    common_errors: list[str]
    feedback: dict[str, str]
    difficulty_levels: dict[str, dict]
    illustrative_only: bool = True


@lru_cache
def load_exercises(directory: str | None = None) -> dict[str, Exercise]:
    path = Path(directory) if directory else settings.exercises_dir
    exercises: dict[str, Exercise] = {}
    for f in sorted(path.glob("*.json")):
        ex = Exercise(**json.loads(f.read_text(encoding="utf-8")))
        exercises[ex.id] = ex
    return exercises


def get_exercise(exercise_id: str) -> Exercise | None:
    return load_exercises().get(exercise_id)
