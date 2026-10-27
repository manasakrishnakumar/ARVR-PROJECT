import numpy as np
import pytest

from app.ml.angle_eval import best_lag, error_metrics, paired_angles

NAMES = ["RIGHT_HIP", "RIGHT_SHOULDER", "RIGHT_ELBOW"]


def _arm(angles_deg, noise=0.0, seed=0):
    """SYNTHETIC skeleton array whose right-arm abduction angle follows `angles_deg` (pixel units, y down)."""
    rng = np.random.default_rng(seed)
    a = np.zeros((len(angles_deg), 33, 4))
    a[:, :, 3] = 1.0
    a[:, 24, :2] = (500, 800)
    a[:, 12, :2] = (500, 500)
    for i, d in enumerate(angles_deg):
        r = np.radians(d)
        a[i, 14, :2] = (500 + 300 * np.sin(r), 500 + 300 * np.cos(r)) + rng.normal(0, noise, 2)
    return a


def test_error_metrics_hand_computed():
    m = error_metrics([(10, 8), (20, 20), (30, 34), (40, 36)])
    assert m["n"] == 4 and m["mae_deg"] == pytest.approx(2.5) and m["bias_deg"] == pytest.approx(0.5)
    assert m["rmse_deg"] == pytest.approx(((4 + 0 + 16 + 16) / 4) ** 0.5)
    assert 0.9 < m["pearson_r"] <= 1.0 and m["loa95_deg"][0] < m["bias_deg"] < m["loa95_deg"][1]
    assert error_metrics([(1, 1)])["mae_deg"] is None  # too few pairs: no invented statistic


def test_identical_sources_have_zero_error_and_missing_landmarks_are_dropped():
    truth = np.linspace(20, 90, 60)
    ref, mp = _arm(truth), _arm(truth)
    mp[10:20, 14, 3] = 0.1  # elbow not visible in 10 frames of the estimated skeleton
    pairs = paired_angles(mp, ref, NAMES, list(range(60)))
    assert len(pairs) == 50 and error_metrics(pairs)["mae_deg"] == pytest.approx(0.0, abs=1e-6)


def test_offset_and_noise_are_measured():
    truth = np.linspace(20, 90, 200)
    ref = _arm(truth)
    mp = _arm(truth + 5.0, noise=0.0)  # estimator reads 5 degrees too high
    m = error_metrics(paired_angles(mp, ref, NAMES, list(range(200))))
    assert m["bias_deg"] == pytest.approx(5.0, abs=0.01) and m["mae_deg"] == pytest.approx(5.0, abs=0.01)


def test_best_lag_detects_a_frame_shift():
    truth = 55 + 30 * np.sin(np.linspace(0, 12, 300))
    ref = _arm(truth)
    mp = _arm(np.roll(truth, -3))  # estimator runs 3 frames ahead of the reference
    lag, maes = best_lag(mp, ref, NAMES, list(range(20, 280)))
    assert lag == 3 and maes[3] < maes[0]
    assert best_lag(ref, ref, NAMES, list(range(20, 280)))[0] == 0
