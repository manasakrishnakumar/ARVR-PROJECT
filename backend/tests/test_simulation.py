import pytest

from app.personalization.controller import AdaptiveConfig
from app.personalization.simulation import (MODELS, abilities, p_acceptable, paired_bootstrap_diff, run_user, simulate)

CFG = AdaptiveConfig.load()


def test_user_models_are_deterministic_and_bounded():
    import random
    for m in MODELS:
        a1, a2 = abilities(m, random.Random(3), 40), abilities(m, random.Random(3), 40)
        assert a1 == a2 and all(0 <= x <= 1 for x in a1)
    assert abilities("improving", random.Random(1), 40)[-1] > abilities("improving", random.Random(1), 40)[0]
    assert abilities("declining", random.Random(1), 40)[-1] < abilities("declining", random.Random(1), 40)[0]


def test_harder_levels_are_less_likely_to_succeed():
    assert p_acceptable(0.5, 1) > p_acceptable(0.5, 2) > p_acceptable(0.5, 3)
    assert p_acceptable(0.95, 3) > 0.85 and p_acceptable(0.1, 1) < 0.1


def test_adaptive_policy_never_violates_safety_limits_in_any_model():
    for m in MODELS:
        for seed in range(30):
            assert run_user(CFG, "adaptive", m, seed)["violations"] == 0


def test_stable_users_settle_and_do_not_oscillate():
    runs = [run_user(CFG, "adaptive", "stable", s) for s in range(60)]
    assert statistics_mean(r["level_changes"] for r in runs) <= 3  # at most the two possible steps, plus a rare correction
    # Known, measured behaviour (see docs/adaptive-controller.md): a user whose ability sits near a level boundary can step up on
    # two lucky sessions and back down after two poor ones, about once per 40 sessions on average. Bounded, not zero.
    assert statistics_mean(r["direction_reversals"] for r in runs) < 1.5


def test_summary_structure_and_bootstrap_interval():
    res = simulate(n_users=15, n_sessions=20, seed=2)
    assert set(res["models"]) == set(MODELS) and res["models"]["stable"]["safety_violations_total"] == 0
    d = res["models"]["improving"]["adaptive_minus_best_fixed_mismatch_share"]
    assert d["ci95"][0] <= d["mean"] <= d["ci95"][1]
    mean, lo, hi = paired_bootstrap_diff([0.1, 0.2, 0.3, 0.2], [0.3, 0.3, 0.4, 0.3])
    assert mean == pytest.approx(-0.125) and lo <= mean <= hi


def statistics_mean(xs):
    import statistics
    return statistics.fmean(xs)
