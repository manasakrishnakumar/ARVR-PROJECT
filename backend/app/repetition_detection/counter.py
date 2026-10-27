"""State-machine repetition counter.

Works on a 1-D joint-angle time series. Angle is normalised to progress p:
p = 0 at the start angle, p = 1 at the target angle (works for increasing or
decreasing angles). Targets are configurable and illustrative, not prescribed.
"""
from dataclasses import dataclass, field
from enum import Enum


class Phase(str, Enum):
    REST = "rest"
    MOVING_OUT = "moving_out"
    TARGET = "target"
    RETURNING = "returning"


@dataclass
class RepConfig:
    start_angle: float
    target_angle: float
    required_fraction: float = 0.75  # progress needed to count as reaching the target
    hysteresis_deg: float = 8.0
    initiation_fraction: float = 0.15
    min_valid_duration_s: float = 0.4  # shorter excursions are treated as noise and ignored
    max_gap_s: float = 2.0  # abort an attempt if no valid angle for this long

    def __post_init__(self) -> None:
        if abs(self.target_angle - self.start_angle) < 1e-6:
            raise ValueError("start and target angles must differ")


@dataclass
class Repetition:
    index: int
    t_start: float
    t_end: float
    peak_progress: float
    times: list[float]
    angles: list[float]
    n_frames: int
    n_missing: int
    reached_target: bool

    @property
    def counted(self) -> bool:
        return self.reached_target

    @property
    def duration_s(self) -> float:
        return self.t_end - self.t_start


@dataclass
class _Attempt:
    t_start: float
    times: list[float] = field(default_factory=list)
    angles: list[float] = field(default_factory=list)
    n_frames: int = 0
    n_missing: int = 0
    peak: float = 0.0
    reached: bool = False


class RepetitionCounter:
    def __init__(self, cfg: RepConfig):
        self.cfg = cfg
        self.phase = Phase.REST
        self.count = 0  # repetitions that reached the required range
        self.attempts: list[Repetition] = []  # every completed excursion (counted or not)
        self._a: _Attempt | None = None
        self._last_valid_t: float | None = None
        self._hyst = cfg.hysteresis_deg / abs(cfg.target_angle - cfg.start_angle)

    def progress(self, angle: float) -> float:
        c = self.cfg
        return (angle - c.start_angle) / (c.target_angle - c.start_angle)

    def update(self, t: float, angle: float | None) -> Repetition | None:
        """Feed one sample. Returns a Repetition when an excursion finishes."""
        c = self.cfg
        if angle is None or angle != angle:
            if self._a is not None:
                self._a.n_frames += 1
                self._a.n_missing += 1
                if self._last_valid_t is not None and t - self._last_valid_t > c.max_gap_s:
                    self._a, self.phase = None, Phase.REST
            return None
        self._last_valid_t = t
        p = self.progress(angle)
        a = self._a

        if self.phase == Phase.REST:
            if p < c.initiation_fraction:
                return None
            self._a = a = _Attempt(t_start=t)
            self.phase = Phase.MOVING_OUT

        assert a is not None
        a.times.append(t)
        a.angles.append(angle)
        a.n_frames += 1
        a.peak = max(a.peak, p)

        if self.phase == Phase.MOVING_OUT:
            if p >= c.required_fraction:
                a.reached = True
                self.phase = Phase.TARGET
            elif p < c.initiation_fraction * 0.5:
                return self._finish(t)
        elif self.phase == Phase.TARGET:
            if p < c.required_fraction - self._hyst:
                self.phase = Phase.RETURNING
        elif self.phase == Phase.RETURNING:
            if p >= c.required_fraction:
                self.phase = Phase.TARGET
            elif p < c.initiation_fraction:
                return self._finish(t)
        return None

    def _finish(self, t: float) -> Repetition | None:
        a = self._a
        self._a, self.phase = None, Phase.REST
        assert a is not None
        if t - a.t_start < self.cfg.min_valid_duration_s:
            return None  # noise, not a movement
        rep = Repetition(
            index=len(self.attempts) + 1, t_start=a.t_start, t_end=t, peak_progress=a.peak,
            times=a.times, angles=a.angles, n_frames=a.n_frames, n_missing=a.n_missing,
            reached_target=a.reached,
        )
        self.attempts.append(rep)
        if rep.counted:
            self.count += 1
        return rep
