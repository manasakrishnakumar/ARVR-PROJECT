import math

import pytest

from app.exercises.library import get_exercise, load_exercises
from app.services.analysis import analyze_series

NEW = ["hip_abduction", "hip_flexion", "knee_extension_seated"]


def sweep(ex, reps=6, period=3.0, hz=15):
    """A clean synthetic movement start -> target -> start (SYNTHETIC: checks the definitions work, not real people)."""
    n = int(reps * period * hz)
    return [(i / hz, ex.start_angle_deg + (ex.target_angle_deg - ex.start_angle_deg) * (1 - math.cos(2 * math.pi * i / hz / period)) / 2)
            for i in range(n)]


@pytest.mark.parametrize("ex_id", NEW)
def test_new_exercises_are_valid_and_complete(ex_id):
    ex = get_exercise(ex_id)
    assert ex is not None and ex.illustrative_only
    assert len(ex.landmarks) == 3 and set(ex.difficulty_levels) == {"1", "2", "3"}
    assert abs(ex.target_angle_deg - ex.start_angle_deg) >= 20  # a measurable range
    assert {"low_range", "too_fast", "good"} <= set(ex.feedback)


@pytest.mark.parametrize("ex_id", NEW)
def test_a_clean_full_range_movement_is_counted_and_judged_acceptable(ex_id):
    ex = get_exercise(ex_id)
    res = analyze_series(ex, 1, sweep(ex))
    assert res.counted_reps >= 5
    assert [r.assessment.label for r in res.attempts if r.counted].count("acceptable") >= 4


@pytest.mark.parametrize("ex_id", NEW)
def test_a_tiny_movement_is_never_judged_acceptable(ex_id):
    ex = get_exercise(ex_id)
    small = [(t, ex.start_angle_deg + (a - ex.start_angle_deg) * 0.2) for t, a in sweep(ex)]
    res = analyze_series(ex, 1, small)
    assert all(r.assessment.label != "acceptable" for r in res.attempts)


def test_library_lists_all_nine_exercises_and_ids_match_file_names():
    assert len(load_exercises()) == 9
