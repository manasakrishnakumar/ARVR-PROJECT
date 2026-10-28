"""Adaptive difficulty controller: a transparent, conservative, deterministic policy.

Independent of the camera, pose estimation and database; its only inputs are summaries of reliable
repetitions. It produces SOFTWARE RECOMMENDATIONS for the next session, not clinical decisions.

Safety design:
- difficulty only changes between sessions, by one level, inside [min_level, max_level];
- an increase needs several reliable repetitions, good pose reliability, and the same 'good' result in
  `confirm_sessions` consecutive sessions at the current level (multi-session hysteresis), and at least
  `min_sessions_at_level` sessions at that level (so levels cannot flip-flop);
- the increase and decrease thresholds are separated by a dead zone ('neutral') that maintains the level;
- unreliable or too little data never raises difficulty;
- a very poor session recommends a pause and never raises difficulty;
- the quality score comes from the rule-based assessment of measured movement, never from a classifier
  that merely predicts a high score.
"""
import json
import statistics
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")
SAFETY_NOTE = ("Software suggestion for a research prototype, not a clinical decision. Follow the guidance of your "
               "qualified rehabilitation professional and stop if you feel discomfort.")
Classification = Literal["insufficient", "good", "neutral", "poor", "severe"]
Action = Literal["increase", "decrease", "maintain", "pause", "reset"]


class IncreaseRule(BaseModel):
    min_quality: float = Field(ge=0, le=1)
    max_error_rate: float = Field(ge=0, le=1)
    min_completion: float = Field(ge=0, le=2)
    max_range_std: float = Field(ge=0)
    confirm_sessions: int = Field(ge=1, le=10)


class DecreaseRule(BaseModel):
    max_quality: float = Field(ge=0, le=1)
    min_error_rate: float = Field(ge=0, le=1)
    confirm_sessions: int = Field(ge=1, le=10)


class PauseRule(BaseModel):
    quality_below: float = Field(ge=0, le=1)
    error_rate_at_least: float = Field(ge=0, le=1)


class PainRule(BaseModel):
    """Self-reported pain (0-10) after a session. Pain only ever makes the suggestion more cautious."""
    no_increase_at: int = Field(default=4, ge=0, le=10)
    pause_at: int = Field(default=7, ge=0, le=10)

    @model_validator(mode="after")
    def _ordered(self) -> "PainRule":
        if self.pause_at < self.no_increase_at:
            raise ValueError("pain.pause_at must not be below pain.no_increase_at")
        return self


class AdaptiveConfig(BaseModel):
    min_level: int = Field(ge=1)
    default_level: int = Field(ge=1)
    min_reliable_reps: int = Field(ge=1)
    min_reliable_fraction: float = Field(ge=0, le=1)
    min_sessions_at_level: int = Field(ge=1, le=10)
    increase: IncreaseRule
    decrease: DecreaseRule
    pause: PauseRule
    pain: PainRule = PainRule()
    feedback_intensity: dict[str, str]

    @model_validator(mode="after")
    def _check_consistency(self) -> "AdaptiveConfig":
        if self.default_level < self.min_level:
            raise ValueError("default_level must be >= min_level")
        if self.decrease.max_quality >= self.increase.min_quality:
            raise ValueError("decrease.max_quality must be below increase.min_quality (a neutral dead zone is required)")
        if self.pause.quality_below > self.decrease.max_quality:
            raise ValueError("pause.quality_below must not exceed decrease.max_quality")
        if self.increase.max_error_rate >= self.decrease.min_error_rate:
            raise ValueError("increase.max_error_rate must be below decrease.min_error_rate")
        return self

    @classmethod
    def load(cls, path: Path | None = None) -> "AdaptiveConfig":
        data = json.loads((path or DEFAULT_CONFIG_PATH).read_text(encoding="utf-8"))
        return cls(**{k: v for k, v in data.items() if not k.startswith("_")})


class RepObs(BaseModel):
    """One repetition as seen by the controller (from the rule-based assessment)."""
    label: str
    score: float | None = Field(default=None, ge=0, le=1)
    reliable: bool
    counted: bool
    peak_progress: float = 0.0


class SessionMetrics(BaseModel):
    n_reps: int
    n_reliable: int
    counted_reps: int
    target_reps: int
    quality: float | None  # mean score of reliable repetitions
    error_rate: float | None  # share of reliable repetitions that were not 'acceptable'
    completion: float  # counted repetitions / target
    range_std: float | None  # spread of achieved range across reliable repetitions
    reliable_fraction: float  # reliable repetitions / all repetitions


class HistoryItem(BaseModel):
    """A past session for the same exercise, newest first in the history list."""
    level: int = Field(ge=1)
    classification: Classification
    action: str = "maintain"


class Recommendation(BaseModel):
    action: Action
    current_level: int
    next_level: int
    target_reps: int
    range_fraction: float
    min_rep_duration_s: float
    feedback_intensity: str
    classification: Classification
    reasons: list[str]
    metrics: SessionMetrics
    safety_note: str = SAFETY_NOTE


def compute_metrics(reps: list[RepObs], target_reps: int) -> SessionMetrics:
    reliable = [r for r in reps if r.reliable and r.score is not None]
    quality = statistics.fmean(r.score for r in reliable) if reliable else None  # type: ignore[misc]
    errors = sum(r.label != "acceptable" for r in reliable)
    return SessionMetrics(
        n_reps=len(reps), n_reliable=len(reliable), counted_reps=sum(r.counted for r in reps), target_reps=target_reps,
        quality=quality, error_rate=(errors / len(reliable)) if reliable else None,
        completion=sum(r.counted for r in reps) / target_reps if target_reps else 0.0,
        range_std=statistics.pstdev(r.peak_progress for r in reliable) if len(reliable) > 1 else None,
        reliable_fraction=len(reliable) / len(reps) if reps else 0.0)


def classify(m: SessionMetrics, cfg: AdaptiveConfig) -> Classification:
    if m.n_reliable < cfg.min_reliable_reps or m.reliable_fraction < cfg.min_reliable_fraction \
            or m.quality is None or m.error_rate is None:
        return "insufficient"
    if m.quality < cfg.pause.quality_below or m.error_rate >= cfg.pause.error_rate_at_least:
        return "severe"
    if m.quality < cfg.decrease.max_quality or m.error_rate > cfg.decrease.min_error_rate:
        return "poor"
    inc = cfg.increase
    if (m.quality >= inc.min_quality and m.error_rate <= inc.max_error_rate and m.completion >= inc.min_completion
            and (m.range_std is None or m.range_std <= inc.max_range_std)):
        return "good"
    return "neutral"


def _streak(history: list[HistoryItem], level: int, wanted: set[str]) -> int:
    """Consecutive most-recent sessions at `level` whose classification is in `wanted`. Anything else (another level,
    insufficient data, neutral) ends the streak, so confirmation always needs fresh, reliable evidence."""
    n = 0
    for h in history:
        if h.level != level or h.classification not in wanted:
            break
        n += 1
    return n


def _sessions_at_level(history: list[HistoryItem], level: int) -> int:
    n = 0
    for h in history:
        if h.level != level:
            break
        n += 1
    return n


def recommend(cfg: AdaptiveConfig, levels: dict[str, dict], current_level: int, reps: list[RepObs],
              history: list[HistoryItem] | None = None, pain: int | None = None) -> Recommendation:
    """levels: the exercise's difficulty_levels (keys '1', '2', ...). history: past sessions of this exercise, newest first."""
    available = sorted(int(k) for k in levels)
    if current_level not in available:
        raise ValueError(f"level {current_level} is not defined for this exercise (options: {available})")
    lo, hi = max(cfg.min_level, available[0]), available[-1]
    history = history or []
    params = levels[str(current_level)]
    metrics = compute_metrics(reps, int(params["target_reps"]))
    cls = classify(metrics, cfg)
    reasons: list[str] = []
    action: Action = "maintain"
    next_level = current_level
    seen_at_level = _sessions_at_level(history, current_level) + 1  # including this session

    if cls == "insufficient":
        reasons.append(f"Not enough reliable data to judge this session ({metrics.n_reliable} reliable repetitions, "
                       f"{metrics.reliable_fraction:.0%} of all; need {cfg.min_reliable_reps} and {cfg.min_reliable_fraction:.0%}). "
                       "Difficulty is kept; it is never raised on unreliable data.")
    elif cls in ("poor", "severe"):
        streak = 1 + _streak(history, current_level, {"poor", "severe"})
        if cls == "severe":
            action = "pause"
            trigger = (f"the average score was very low ({metrics.quality:.2f})" if metrics.quality < cfg.pause.quality_below
                       else f"{metrics.error_rate:.0%} of the repetitions were flagged (average score {metrics.quality:.2f})")
            reasons.append(f"This session was difficult: {trigger}. Consider a break and check with your rehabilitation professional.")
        if streak >= cfg.decrease.confirm_sessions and current_level > lo:
            next_level = current_level - 1
            action = "decrease" if cls == "poor" else action
            reasons.append(f"Low quality in {streak} consecutive sessions at level {current_level}: lowering to level {next_level}.")
        else:
            if cls == "poor":
                reasons.append(f"Low quality this session (score {metrics.quality:.2f}, {metrics.error_rate:.0%} flagged). "
                               f"{streak} of {cfg.decrease.confirm_sessions} sessions needed before lowering the level.")
            if current_level == lo and streak >= cfg.decrease.confirm_sessions:
                reasons.append("Already at the lowest level.")
    elif cls == "good":
        streak = 1 + _streak(history, current_level, {"good"})
        if current_level >= hi:
            reasons.append("Good session, already at the highest level for this exercise.")
        elif streak >= cfg.increase.confirm_sessions and seen_at_level >= cfg.min_sessions_at_level:
            next_level = current_level + 1
            action = "increase"
            reasons.append(f"Good, reliable sessions {streak} times in a row at level {current_level} "
                           f"(score {metrics.quality:.2f}, {metrics.error_rate:.0%} flagged): a small step up to level {next_level}.")
        else:
            reasons.append(f"Good session (score {metrics.quality:.2f}). {min(streak, cfg.increase.confirm_sessions)} of "
                           f"{cfg.increase.confirm_sessions} confirming sessions needed before raising the level.")
    else:
        reasons.append(f"Moderate performance (score {metrics.quality:.2f}, {metrics.error_rate:.0%} flagged): keeping level {current_level}.")

    if pain is not None and pain >= cfg.pain.pause_at:
        action, next_level = "pause", current_level
        reasons.append(f"You reported pain {pain}/10. Stop for now, keep the level, and talk to your rehabilitation professional "
                       "before continuing. Difficulty is never raised after reported pain.")
    elif pain is not None and pain >= cfg.pain.no_increase_at and next_level > current_level:
        action, next_level = "maintain", current_level
        reasons.append(f"You reported pain {pain}/10, so the level is not raised even though the session went well.")
    elif pain is not None and pain >= cfg.pain.no_increase_at:
        reasons.append(f"You reported pain {pain}/10. Take care and stop if it gets worse.")

    nxt = levels[str(next_level)]
    return Recommendation(
        action=action, current_level=current_level, next_level=next_level, target_reps=int(nxt["target_reps"]),
        range_fraction=float(nxt["range_fraction"]), min_rep_duration_s=float(nxt["min_rep_duration_s"]),
        feedback_intensity=cfg.feedback_intensity.get(cls, "normal"), classification=cls, reasons=reasons, metrics=metrics)


def reset_to_default(cfg: AdaptiveConfig, levels: dict[str, dict]) -> Recommendation:
    """Explicit reset to the safe default level (user or clinician request)."""
    available = sorted(int(k) for k in levels)
    level = min(max(cfg.default_level, available[0]), available[-1])
    p = levels[str(level)]
    return Recommendation(
        action="reset", current_level=level, next_level=level, target_reps=int(p["target_reps"]),
        range_fraction=float(p["range_fraction"]), min_rep_duration_s=float(p["min_rep_duration_s"]),
        feedback_intensity="normal", classification="insufficient",
        reasons=[f"Reset to the default level {level}."], metrics=compute_metrics([], int(p["target_reps"])))
