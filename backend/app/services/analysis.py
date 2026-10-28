"""Pipeline: angle -> smoothing -> repetition counting -> features -> rule-based assessment.

StreamAnalyzer holds the per-session state so the same logic serves batch evaluation
(analyze_series) and live WebSocket streaming. With calibrate=True the counting range is measured from the user's own movement
in the first seconds; repetitions performed during calibration are replayed through the counter, so none are lost.
"""
from dataclasses import dataclass, field

from app.angle_calculation.angles import AngleSmoother
from app.exercise_assessment.rules import Assessment, assess_rep, level_params
from app.exercises.library import Exercise
from app.feature_extraction.features import rep_features
from app.repetition_detection.calibration import MIN_SECONDS, MIN_VALID, estimate_range
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
    reps: list[RepResult] = field(default_factory=list)  # repetitions that finished on this frame (several after a calibration replay)
    calibrating: bool = False
    calibrated: tuple[float, float] | None = None  # set on the frame calibration completes: (start, target)

    @property
    def rep(self) -> RepResult | None:
        return self.reps[-1] if self.reps else None


class StreamAnalyzer:
    def __init__(self, ex: Exercise, difficulty: int, calibrate: bool = False):
        self.ex, self.difficulty = ex, difficulty
        self.level = level_params(ex, difficulty)  # raises ValueError for unknown difficulty
        self.smoother = AngleSmoother()
        self.calibrating = calibrate
        self.calibrated_range: tuple[float, float] | None = None
        self._buf: list[tuple[float, float | None]] = []
        self.counter = None if calibrate else self._make_counter(ex.start_angle_deg, ex.target_angle_deg, ex.hysteresis_deg)

    def _make_counter(self, start: float, target: float, hysteresis_deg: float) -> RepetitionCounter:
        return RepetitionCounter(RepConfig(start_angle=start, target_angle=target, required_fraction=self.level["range_fraction"],
                                           hysteresis_deg=hysteresis_deg))

    def _finish(self, rep: Repetition) -> RepResult:
        return RepResult(rep, rep.counted, assess_rep(self.ex, self.difficulty, rep_features(rep)))

    def push(self, t: float, angle: float | None) -> StreamUpdate:
        # missing frames must reach the counter as None so reliability reflects real dropouts
        smoothed = self.smoother.update(angle) if angle is not None else None
        shown = self.smoother.value

        if self.calibrating:
            self._buf.append((t, smoothed))
            valid = [v for _, v in self._buf if v is not None]
            if len(valid) >= MIN_VALID and self._buf[-1][0] - self._buf[0][0] >= MIN_SECONDS:
                rng = estimate_range(valid, self.ex)
                if rng is not None:
                    start, target = rng
                    self.calibrated_range, self.calibrating = rng, False
                    self.counter = self._make_counter(start, target, 0.1 * abs(target - start))
                    reps = [r for r in (self.counter.update(bt, bv) for bt, bv in self._buf) if r is not None]
                    self._buf = []
                    return StreamUpdate(self.counter.phase.value, self.counter.count, shown,
                                        self.counter.progress(shown) if shown is not None else None,
                                        [self._finish(r) for r in reps], False, rng)
            return StreamUpdate("calibrating", 0, shown, None, [], True)

        assert self.counter is not None
        rep = self.counter.update(t, smoothed)
        return StreamUpdate(self.counter.phase.value, self.counter.count, shown,
                            self.counter.progress(shown) if shown is not None else None,
                            [self._finish(rep)] if rep is not None else [])


def analyze_series(ex: Exercise, difficulty: int, samples: list[tuple[float, float | None]], calibrate: bool = False) -> SeriesResult:
    sa = StreamAnalyzer(ex, difficulty, calibrate)
    results = [r for t, a in samples for r in sa.push(t, a).reps]
    return SeriesResult(sa.counter.count if sa.counter else 0, results, sa.counter.phase.value if sa.counter else "calibrating")
