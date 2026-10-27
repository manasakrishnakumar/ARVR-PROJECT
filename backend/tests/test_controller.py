import json
import random

import pytest

from app.exercises.library import get_exercise
from app.personalization.controller import (DEFAULT_CONFIG_PATH, AdaptiveConfig, HistoryItem, RepObs, classify,
                                            compute_metrics, recommend, reset_to_default)

CFG = AdaptiveConfig.load()
LEVELS = get_exercise("elbow_flexion").difficulty_levels  # 3 levels, target reps 5 / 8 / 10


def reps(n=6, score=0.95, bad=0, reliable=True, counted=True, peak=0.9, jitter=0.0, seed=0):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        is_bad = i < bad
        out.append(RepObs(label="insufficient_range" if is_bad else "acceptable", score=min(1.0, max(0.0, score + rng.uniform(-jitter, jitter))),
                          reliable=reliable, counted=counted, peak_progress=peak + rng.uniform(-jitter, jitter)))
    return out


def good_session():
    return reps(n=6, score=0.95)  # 6 reps >= target 5 at level 1; but level 2 needs 8


def rec(level=1, r=None, history=None):
    return recommend(CFG, LEVELS, level, r if r is not None else good_session(), history)


def good_at(level, n=1):
    return [HistoryItem(level=level, classification="good", action="maintain") for _ in range(n)]


# ---- configuration ----------------------------------------------------------------------------

def test_default_config_loads_and_is_consistent():
    assert CFG.decrease.max_quality < CFG.increase.min_quality  # dead zone between the two policies
    assert CFG.increase.confirm_sessions >= 2 and CFG.min_sessions_at_level >= 2


def test_inconsistent_config_is_rejected(tmp_path):
    data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["decrease"]["max_quality"] = 0.9  # >= increase.min_quality: no dead zone, would allow oscillation
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        AdaptiveConfig.load(p)


# ---- safety: unreliable data never raises difficulty --------------------------------------------

def test_too_few_reliable_reps_keeps_level_even_if_perfect():
    r = rec(1, reps(n=3, score=1.0), good_at(1, 5))
    assert r.classification == "insufficient" and r.action == "maintain" and r.next_level == 1


def test_low_reliable_fraction_keeps_level():
    mixed = reps(n=6, score=1.0) + reps(n=10, reliable=False, score=0.0)
    r = rec(1, mixed, good_at(1, 5))
    assert r.classification == "insufficient" and r.next_level == 1 and "never raised" in r.reasons[0]


def test_unreliable_repetitions_are_excluded_from_quality():
    m = compute_metrics(reps(n=5, score=0.9) + reps(n=2, score=0.0, reliable=False), 5)
    assert m.n_reliable == 5 and m.quality == pytest.approx(0.9) and m.reliable_fraction == pytest.approx(5 / 7)


# ---- hysteresis / multi-session confirmation -----------------------------------------------------

def test_single_good_session_does_not_increase():
    r = rec(1, good_session(), [])
    assert r.classification == "good" and r.action == "maintain" and r.next_level == 1 and "1 of 2" in r.reasons[0]


def test_two_consecutive_good_sessions_increase_by_exactly_one_level():
    r = rec(1, good_session(), good_at(1, 1))
    assert r.action == "increase" and r.next_level == 2
    assert r.target_reps == int(LEVELS["2"]["target_reps"]) and r.range_fraction == LEVELS["2"]["range_fraction"]


def test_no_immediate_second_step_after_a_level_change():
    # the session just played was the first at level 2 (previous session was at level 1): streak resets
    r = rec(2, reps(n=8, score=0.95), [HistoryItem(level=1, classification="good", action="increase")])
    assert r.action == "maintain" and r.next_level == 2


def test_neutral_or_insufficient_session_breaks_the_streak():
    for broken in ("neutral", "insufficient", "poor"):
        hist = [HistoryItem(level=1, classification=broken), HistoryItem(level=1, classification="good")]
        assert rec(1, good_session(), hist).action == "maintain", broken


def test_cannot_exceed_highest_level():
    r = rec(3, reps(n=10, score=0.97), good_at(3, 5))
    assert r.next_level == 3 and r.action == "maintain" and "highest level" in r.reasons[0]


def test_incomplete_or_inconsistent_sessions_are_not_good():
    assert classify(compute_metrics(reps(n=4, score=0.95), 5), CFG) == "insufficient"  # < min reliable reps
    assert classify(compute_metrics(reps(n=6, score=0.95, counted=False), 5), CFG) == "neutral"  # target not completed
    assert classify(compute_metrics(reps(n=8, score=0.95, jitter=0.0) + [RepObs(label="acceptable", score=0.95, reliable=True, counted=True, peak_progress=0.2)] * 4, 5), CFG) == "neutral"  # erratic range


def test_a_good_score_alone_is_not_enough_error_rate_matters():
    m = compute_metrics(reps(n=10, score=0.95, bad=3), 5)  # 30% flagged > 20% allowed
    assert classify(m, CFG) == "neutral"


# ---- decreasing and pausing ---------------------------------------------------------------------

def test_poor_once_maintains_poor_twice_decreases():
    poor = reps(n=6, score=0.4, bad=4)
    once = rec(2, poor, [])
    assert once.classification == "poor" and once.action == "maintain" and once.next_level == 2
    twice = rec(2, poor, [HistoryItem(level=2, classification="poor")])
    assert twice.action == "decrease" and twice.next_level == 1


def test_never_goes_below_the_minimum_level():
    poor = reps(n=6, score=0.4, bad=4)
    r = rec(1, poor, [HistoryItem(level=1, classification="poor")] * 3)
    assert r.next_level == 1 and r.action == "maintain"


def test_severe_session_recommends_pause_and_never_increases():
    r = rec(2, reps(n=6, score=0.1, bad=6), good_at(2, 5))
    assert r.classification == "severe" and r.action == "pause" and r.next_level == 2
    assert "break" in r.reasons[0].lower() and r.feedback_intensity == "high"


def test_pause_reason_names_the_real_trigger():
    low_score = rec(2, reps(n=6, score=0.1, bad=6))
    assert "average score was very low" in low_score.reasons[0]
    all_flagged_but_decent_score = rec(2, reps(n=6, score=0.72, bad=6))  # partial-credit scores, every repetition flagged
    assert all_flagged_but_decent_score.classification == "severe" and "100% of the repetitions were flagged" in all_flagged_but_decent_score.reasons[0]
    assert "very low" not in all_flagged_but_decent_score.reasons[0]


def test_unknown_level_is_an_error():
    with pytest.raises(ValueError):
        rec(7)


def test_reset_returns_the_safe_default():
    r = reset_to_default(CFG, LEVELS)
    assert r.action == "reset" and r.next_level == CFG.default_level and "Reset" in r.reasons[0]


def test_recommendation_always_carries_the_safety_note():
    assert "not a clinical decision" in rec(1).safety_note


# ---- properties over long simulated histories (SYNTHETIC sessions: software verification only) ------

def _simulate(seed, n_sessions=300):
    rng = random.Random(seed)
    level, history, trace = 1, [], []
    for _ in range(n_sessions):
        q = rng.choice([0.1, 0.35, 0.6, 0.8, 0.9, 0.97]) if rng.random() < 0.5 else rng.uniform(0, 1)
        n = rng.choice([2, 5, 6, 8, 10])
        bad = int(round(n * (1 - q) * rng.uniform(0.5, 1.2)))
        r = recommend(CFG, LEVELS, level, reps(n=n, score=q, bad=min(n, bad), reliable=rng.random() > 0.1,
                                                counted=rng.random() > 0.1, seed=rng.randrange(10**6), jitter=0.05, peak=0.9), history)
        trace.append((level, r))
        history.insert(0, HistoryItem(level=level, classification=r.classification, action=r.action))
        level = r.next_level
    return trace


@pytest.mark.parametrize("seed", range(8))
def test_random_histories_respect_all_safety_invariants(seed):
    trace = _simulate(seed)
    last_change = None
    for i, (level, r) in enumerate(trace):
        assert 1 <= r.next_level <= 3                                   # bounds
        assert abs(r.next_level - level) <= 1                           # one step at a time
        if r.next_level > level:                                         # increases need a good, reliable session
            assert r.classification == "good" and r.metrics.n_reliable >= CFG.min_reliable_reps
        if r.classification != "good":                                   # never raised on anything but a good session
            assert r.next_level <= level
        if r.action == "pause":
            assert r.next_level <= level
        if r.next_level != level:                                        # no flip-flopping: minimum dwell of 2 sessions
            if last_change is not None:
                assert i - last_change >= 2
            last_change = i


def test_alternating_good_and_poor_sessions_never_change_the_level():
    level, history = 2, []
    for i in range(40):
        r = recommend(CFG, LEVELS, level, good_session() if i % 2 == 0 else reps(n=6, score=0.4, bad=4), history)
        assert r.next_level == 2
        history.insert(0, HistoryItem(level=level, classification=r.classification, action=r.action))


def test_performance_hovering_at_the_threshold_changes_level_rarely():
    rng, level, history, changes = random.Random(1), 1, [], 0
    for _ in range(200):
        q = 0.85 + rng.uniform(-0.04, 0.04)  # right around the increase threshold
        r = recommend(CFG, LEVELS, level, reps(n=10, score=q, jitter=0.0), history)
        changes += r.next_level != level
        history.insert(0, HistoryItem(level=level, classification=r.classification, action=r.action))
        level = r.next_level
    assert changes <= 4  # level is capped at 3 and each change needs fresh confirmation
