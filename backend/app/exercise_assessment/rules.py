"""Configurable rule-based baseline for repetition quality.

Reports 'insufficient_data' instead of guessing when measurements are unreliable.
Labels describe observable movement in one camera view, not medical findings.
"""
from dataclasses import dataclass

from app.exercises.library import Exercise

MIN_RELIABILITY = 0.7
MAX_EXTRA_REVERSALS = 2

DEFAULT_FEEDBACK = {
    "acceptable": "Good repetition.",
    "insufficient_range": "Move a little further, within your comfort.",
    "incomplete_repetition": "Try to complete the full movement and return to the start.",
    "too_fast": "Slow down the movement.",
    "uncontrolled": "Keep your movement controlled.",
    "insufficient_data": "Pose not detected clearly. Adjust your position.",
}


@dataclass
class Assessment:
    label: str
    score: float | None
    reliable: bool
    explanation: str
    feedback: str
    features: dict[str, float]


def level_params(ex: Exercise, difficulty: int) -> dict:
    key = str(difficulty)
    if key not in ex.difficulty_levels:
        raise ValueError(f"difficulty {difficulty} not defined for {ex.id}; options: {sorted(ex.difficulty_levels)}")
    return ex.difficulty_levels[key]


def assess_rep(ex: Exercise, difficulty: int, f: dict[str, float]) -> Assessment:
    lv = level_params(ex, difficulty)
    need, min_dur = lv["range_fraction"], lv["min_rep_duration_s"]
    fb = dict(DEFAULT_FEEDBACK)
    for label, key in (("insufficient_range", "low_range"), ("too_fast", "too_fast"), ("acceptable", "good")):
        if key in ex.feedback:
            fb[label] = ex.feedback[key]

    def out(label: str, score: float | None, why: str, reliable: bool = True) -> Assessment:
        return Assessment(label, score, reliable, why, fb[label], f)

    if f["reliability"] < MIN_RELIABILITY:
        return out("insufficient_data", None,
                   f"Only {f['reliability']:.0%} of frames had a reliable angle (need {MIN_RELIABILITY:.0%}).", False)

    score = min(1.0, f["peak_progress"] / need) * min(1.0, f["duration_s"] / min_dur)
    if f["peak_progress"] < need:
        label = "incomplete_repetition" if f["peak_progress"] < 0.4 else "insufficient_range"
        return out(label, score, f"Reached {f['peak_progress']:.0%} of the illustrative range; level {difficulty} expects {need:.0%}.")
    if f["duration_s"] < min_dur:
        return out("too_fast", score, f"Repetition took {f['duration_s']:.1f}s; level {difficulty} expects at least {min_dur:.1f}s.")
    if f["extra_reversals"] > MAX_EXTRA_REVERSALS:
        return out("uncontrolled", min(score, 0.6), f"{int(f['extra_reversals'])} extra direction changes during the repetition.")
    return out("acceptable", 1.0, "Range, pace and direction within the configured limits.")
