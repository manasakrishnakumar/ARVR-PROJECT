import os
import tempfile

os.environ["ARVR_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/p3.db"

import pytest
from fastapi.testclient import TestClient

from app.angle_calculation.angles import AngleSmoother
from app.exercises.library import get_exercise
from app.feature_extraction.features import rep_features
from app.main import app
from app.repetition_detection.counter import Phase, RepConfig, RepetitionCounter
from app.services.analysis import analyze_series
from app.synthetic.sequences import make_sequence

ELBOW = get_exercise("elbow_flexion")  # illustrative: 160 deg -> 50 deg


def run(seq, **cfg):
    c = RepetitionCounter(RepConfig(start_angle=160, target_angle=50, **cfg))
    for t, a in seq:
        c.update(t, a)
    return c


def test_counts_clean_synthetic_reps():
    c = run(make_sequence(160, 50, 5))
    assert c.count == 5 and c.phase == Phase.REST


def test_increasing_angle_direction_also_works():
    c = RepetitionCounter(RepConfig(start_angle=20, target_angle=90))
    for t, a in make_sequence(20, 90, 3):
        c.update(t, a)
    assert c.count == 3


def test_shallow_reps_are_attempts_not_counted():
    c = run(make_sequence(160, 50, 4, depth=0.5))
    assert c.count == 0 and len(c.attempts) == 4


def test_noise_jitter_at_rest_is_not_counted():
    seq = [(i / 30, 160 + (12 if i % 2 else -12)) for i in range(300)]  # +/-12 deg, < initiation threshold
    assert run(seq).count == 0


def test_short_spike_ignored_by_min_duration():
    seq = [(i / 30, 160) for i in range(30)] + [(1 + i / 30, 60) for i in range(3)] + [(1.1 + i / 30, 160) for i in range(30)]
    assert run(seq).count == 0


def test_repeated_identical_frames_do_nothing():
    assert run([(i / 30, 160.0) for i in range(500)]).count == 0


def test_dropout_and_noise_still_count():
    c = RepetitionCounter(RepConfig(start_angle=160, target_angle=50))
    sm = AngleSmoother()
    for t, a in make_sequence(160, 50, 4, noise_deg=2, dropout=0.1, seed=3):
        c.update(t, sm.update(a) if a is not None else None)
    assert c.count == 4


def test_long_gap_aborts_attempt():
    c = RepetitionCounter(RepConfig(start_angle=160, target_angle=50))
    for i in range(30):
        c.update(i / 30, 160 - i * 1.5)  # reaches ~41% of range: moving out, target not reached
    assert c.phase == Phase.MOVING_OUT
    for i in range(30, 150):
        c.update(i / 30, None)
    assert c.phase == Phase.REST and c.count == 0


def test_bad_config_rejected():
    with pytest.raises(ValueError):
        RepConfig(start_angle=90, target_angle=90)


def test_smoother_accepts_persistent_jump():
    s = AngleSmoother(alpha=0.5, max_jump_deg=30, max_rejects=3)
    s.update(90)
    assert s.update(170) == 90 and s.update(170) == 90
    assert s.update(170) == 170


def test_features_of_clean_rep():
    rep = run(make_sequence(160, 50, 1)).attempts[0]
    f = rep_features(rep)
    # excursion window starts at 15% progress, so ROM is ~85% of the 110 deg range
    assert 85 < f["rom_deg"] <= 110 and f["reliability"] == 1.0 and f["extra_reversals"] == 0


def test_pipeline_acceptable_vs_shallow_vs_fast():
    good = analyze_series(ELBOW, 1, make_sequence(160, 50, 3, period_s=3))
    assert good.counted_reps == 3 and all(r.assessment.label == "acceptable" for r in good.attempts)
    shallow = analyze_series(ELBOW, 1, make_sequence(160, 50, 2, depth=0.55))
    assert {r.assessment.label for r in shallow.attempts} == {"insufficient_range"}
    fast = analyze_series(ELBOW, 1, make_sequence(160, 50, 2, period_s=0.8))
    assert {r.assessment.label for r in fast.attempts} == {"too_fast"}


def test_low_reliability_gives_insufficient_data_not_a_guess():
    res = analyze_series(ELBOW, 1, make_sequence(160, 50, 2, dropout=0.45, seed=1))
    for r in res.attempts:
        assert r.assessment.label == "insufficient_data" and not r.assessment.reliable and r.assessment.score is None


def test_unknown_difficulty_raises():
    with pytest.raises(ValueError):
        analyze_series(ELBOW, 4, make_sequence(160, 50, 1))


def test_api_evaluate_and_validation():
    seq = [{"t": t, "angle": a} for t, a in make_sequence(160, 50, 2)]
    with TestClient(app) as c:
        r = c.post("/api/assessment/evaluate", json={"exercise_id": "elbow_flexion", "samples": seq})
        assert r.status_code == 200
        body = r.json()
        assert body["counted_reps"] == 2 and body["method"] == "rule_based" and "medical" in body["disclaimer"].lower()
        assert c.post("/api/assessment/evaluate", json={"exercise_id": "nope", "samples": seq}).status_code == 404
        assert c.post("/api/assessment/evaluate", json={"exercise_id": "elbow_flexion", "samples": seq[:1]}).status_code == 422
        assert c.post("/api/assessment/evaluate", json={"exercise_id": "elbow_flexion", "difficulty": 4, "samples": seq}).status_code == 422
        assert c.post("/api/assessment/evaluate", json={"exercise_id": "elbow_flexion", "samples": seq[::-1]}).status_code == 422
