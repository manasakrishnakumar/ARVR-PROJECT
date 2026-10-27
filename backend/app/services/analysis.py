"""Pipeline: angle series -> smoothing -> repetition counting -> features -> rule-based assessment."""
from dataclasses import dataclass

from app.angle_calculation.angles import AngleSmoother
from app.exercise_assessment.rules import Assessment, assess_rep, level_params
from app.exercises.library import Exercise
from app.feature_extraction.features import rep_features
from app.repetition_detection.counter import RepConfig, Repetition, RepetitionCounter


@dataclass
class RepResult:
    repetition: Repetition
    counted: bool
    assessment: Assessment


@dataclass
class SeriesResult:
    counted_reps: int
    attempts: list[RepResult]
    final_phase: str


def analyze_series(ex: Exercise, difficulty: int, samples: list[tuple[float, float | None]]) -> SeriesResult:
    lv = level_params(ex, difficulty)
    counter = RepetitionCounter(RepConfig(
        start_angle=ex.start_angle_deg, target_angle=ex.target_angle_deg,
        required_fraction=lv["range_fraction"], hysteresis_deg=ex.hysteresis_deg,
    ))
    smoother = AngleSmoother()
    results: list[RepResult] = []
    for t, angle in samples:
        # missing frames must reach the counter as None so reliability reflects real dropouts
        rep = counter.update(t, smoother.update(angle) if angle is not None else None)
        if rep is not None:
            results.append(RepResult(rep, rep.counted, assess_rep(ex, difficulty, rep_features(rep))))
    return SeriesResult(counter.count, results, counter.phase.value)
