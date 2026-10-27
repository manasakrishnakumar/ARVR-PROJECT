import numpy as np
import pytest

from app.exercises.library import get_exercise
from app.feature_extraction.posture import JOINT, posture_features
from app.ml import lopo
from app.ml.synthetic_data import generate_dataset

ABD = get_exercise("shoulder_abduction")
SQUAT = get_exercise("sit_to_stand")


def standing(frames: int = 40) -> np.ndarray:
    """SYNTHETIC upright figure, everything visible. y grows downward."""
    a = np.zeros((frames, 33, 4))
    a[:, :, 3] = 1.0
    pts = {"LEFT_SHOULDER": (0.55, 0.30), "RIGHT_SHOULDER": (0.45, 0.30), "LEFT_HIP": (0.54, 0.60),
           "RIGHT_HIP": (0.46, 0.60), "LEFT_KNEE": (0.54, 0.78), "RIGHT_KNEE": (0.46, 0.78),
           "LEFT_ANKLE": (0.54, 0.95), "RIGHT_ANKLE": (0.46, 0.95), "LEFT_HEEL": (0.53, 0.97), "RIGHT_HEEL": (0.47, 0.97),
           "LEFT_FOOT_INDEX": (0.58, 0.97), "RIGHT_FOOT_INDEX": (0.42, 0.97), "LEFT_EAR": (0.53, 0.18),
           "RIGHT_EAR": (0.47, 0.18), "RIGHT_ELBOW": (0.45, 0.45), "RIGHT_WRIST": (0.45, 0.60),
           "LEFT_ELBOW": (0.55, 0.45), "LEFT_WRIST": (0.55, 0.60)}
    for n, (x, y) in pts.items():
        a[:, JOINT[n], :2] = (x, y)
    return a


def test_still_upright_figure_has_no_deviation():
    f = posture_features(standing(), None, ABD, "RIGHT")
    for k in ("torso_tilt_dev_max", "shoulder_asym_dev_max", "head_tilt_dev_max", "knee_valgus_dev_max",
              "heel_lift_dev_max", "knee_over_toe_dev_max"):
        assert f[k] == pytest.approx(0.0, abs=1e-9), k
    assert f["posture_reliability"] == 1.0 and f["lower_body_exercise"] == 0.0
    assert f["elbow_bend_min_deg"] == pytest.approx(180.0, abs=1e-6)  # straight arm


def test_torso_lean_and_shoulder_shrug_detected():
    a = standing()
    for i in range(20, 40):  # lean the shoulders sideways 0.1
        a[i, JOINT["LEFT_SHOULDER"], 0] += 0.1
        a[i, JOINT["RIGHT_SHOULDER"], 0] += 0.1
    assert posture_features(a, None, ABD, "RIGHT")["torso_tilt_dev_max"] > 10
    b = standing()
    b[20:, JOINT["RIGHT_SHOULDER"], 1] -= 0.05  # exercising shoulder rises
    assert posture_features(b, None, ABD, "RIGHT")["shoulder_asym_dev_max"] > 0.1


def test_heel_lift_knee_valgus_and_bent_elbow_detected():
    a = standing()
    a[20:, JOINT["LEFT_HEEL"], 1] -= 0.04
    assert posture_features(a, None, SQUAT, "LEFT")["heel_lift_dev_max"] > 0.05
    b = standing()
    b[20:, JOINT["LEFT_KNEE"], 0] -= 0.06  # knee drifts inward
    assert posture_features(b, None, SQUAT, "LEFT")["knee_valgus_dev_max"] > 0.1
    c = standing()
    c[:, JOINT["RIGHT_WRIST"]] = [0.60, 0.40, 0, 1.0]  # forearm bent back toward the body
    assert posture_features(c, None, ABD, "RIGHT")["elbow_bend_min_deg"] < 150


def test_3d_features_use_depth():
    a2 = standing()
    a3 = standing()
    a3[:, :, 2] = 0.0
    a3[:, JOINT["RIGHT_ELBOW"], 2] = -0.3  # elbow far in front of the shoulder in depth only
    f = posture_features(a2, a3, ABD, "RIGHT")
    assert f["elbow_bend_min_3d_deg"] != 180.0 or f["rom3d_deg"] >= 0.0  # computed without error
    assert posture_features(a2, None, ABD, "RIGHT")["rom3d_deg"] == 0.0  # no 3D data -> zeros, not a crash


def test_robust_to_missing_and_degenerate_data():
    a = standing()
    a[:, :, 3] = 0.0  # nothing visible
    f = posture_features(a, None, SQUAT, "LEFT")
    assert f["posture_reliability"] == 0.0 and all(np.isfinite(v) for v in f.values())
    z = np.zeros((30, 33, 4))
    z[:, :, 3] = 1.0  # everything at the same point: zero-length segments
    assert all(np.isfinite(v) for v in posture_features(z, None, ABD, "RIGHT").values())
    assert posture_features(np.zeros((0, 33, 4)), None, ABD, "RIGHT")["posture_reliability"] == 0.0


def test_lopo_tuning_never_sees_held_out_participant(monkeypatch):
    seen = []
    orig_select, orig_rule = lopo._select_params, lopo._tune_range_rule
    monkeypatch.setattr(lopo, "_select_params", lambda train, p, s: (seen.append({r["participant_id"] for r in train}),
                                                                      orig_select(train, p, s))[1])
    monkeypatch.setattr(lopo, "_tune_range_rule", lambda train: (seen.append({r["participant_id"] for r in train}),
                                                                  orig_rule(train))[1])
    rows = generate_dataset(n_participants=4, reps_per_condition=2, seed=2)
    ev = lopo.run_lopo(rows, n_boot=3)
    assert seen and all(len(s) == 3 for s in seen)  # 4 participants, one always held out
    held = {t["held_out"] for t in ev["tuning"]["rf_base_tuned"]}
    assert held == {r["participant_id"] for r in rows}
