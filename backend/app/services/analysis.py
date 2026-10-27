"""Pipeline: angle -> smoothing -> repetition counting -> features -> rule-based assessment.

StreamAnalyzer holds the per-session state so the same logic serves batch evaluation
(analyze_series) and live WebSocket streaming.
"""
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


@dataclass
class StreamUpdate:
    phase: str
    counted_reps: int
    angle: float | None  # smoothed, None until the first valid sample
    progress: float | None
    rep: RepResult | None  # set on the frame where an excursion finishes


class StreamAnalyzer:
    def __init__(self, ex: Exercise, difficulty: int):
        self.ex, self.difficulty = ex, difficulty
        self.level = level_params(ex, difficulty)  # raises ValueError for unknown difficulty
        self.counter = RepetitionCounter(RepConfig(
            start_angle=ex.start_angle_deg, target_angle=ex.target_angle_deg,
            required_fraction=self.level["range_fraction"], hysteresis_deg=ex.hysteresis_deg,
        ))
        self.smoother = AngleSmoother()

    def push(self, t: float, angle: float | None) -> StreamUpdate:
        # missing frames must reach the counter as None so reliability reflects real dropouts
        smoothed = self.smoother.update(angle) if angle is not None else None
        rep = self.counter.update(t, smoothed)
        result = None
        if rep is not None:
            result = RepResult(rep, rep.counted, assess_rep(self.ex, self.difficulty, rep_features(rep)))
        shown = self.smoother.value
        return StreamUpdate(
            phase=self.counter.phase.value, counted_reps=self.counter.count, angle=shown,
            progress=self.counter.progress(shown) if shown is not None else None, rep=result,
        )


def analyze_series(ex: Exercise, difficulty: int, samples: list[tuple[float, float | None]]) -> SeriesResult:
    sa = StreamAnalyzer(ex, difficulty)
    results = [u.rep for t, a in samples if (u := sa.push(t, a)).rep is not None]
    return SeriesResult(sa.counter.count, results, sa.counter.phase.value)
