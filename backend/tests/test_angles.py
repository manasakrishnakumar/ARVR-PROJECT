import math
from app.angle_calculation.angles import AngleSmoother, Landmark as L, joint_angle


def test_right_angle():
    assert math.isclose(joint_angle(L(1, 0), L(0, 0), L(0, 1)), 90.0)


def test_straight_and_folded():
    assert math.isclose(joint_angle(L(-1, 0), L(0, 0), L(1, 0)), 180.0, abs_tol=1e-6)
    assert math.isclose(joint_angle(L(1, 0), L(0, 0), L(2, 0)), 0.0, abs_tol=1e-6)


def test_missing_low_conf_invalid_and_degenerate():
    assert joint_angle(None, L(0, 0), L(0, 1)) is None
    assert joint_angle(L(1, 0, confidence=0.1), L(0, 0), L(0, 1)) is None
    assert joint_angle(L(float("nan"), 0), L(0, 0), L(0, 1)) is None
    assert joint_angle(L(0, 0), L(0, 0), L(0, 1)) is None


def test_smoother_handles_gap_and_spike():
    s = AngleSmoother(alpha=0.5, max_jump_deg=30)
    assert s.update(None) is None
    assert s.update(90) == 90
    assert s.update(None) == 90
    assert s.update(170) == 90  # spike rejected
    assert s.update(100) == 95
