"""Posture features for one repetition, from MediaPipe landmark arrays of shape (frames, 33, 4) = x, y, z, visibility.

2D arrays hold normalised image coordinates; 3D arrays hold MediaPipe world landmarks (estimated depth, metres).
Deviation features compare each frame with the repetition's own starting posture (median of its first 5 valid
frames), so they measure change during the movement rather than a person's resting posture.
All values are single-camera estimates, not clinical measurements.
"""
import math

import numpy as np

from app.angle_calculation.angles import Landmark, joint_angle
from app.exercises.library import Exercise

MIN_VIS = 0.5
JOINT = {"NOSE": 0, "LEFT_EAR": 7, "RIGHT_EAR": 8, "LEFT_SHOULDER": 11, "RIGHT_SHOULDER": 12, "LEFT_ELBOW": 13,
         "RIGHT_ELBOW": 14, "LEFT_WRIST": 15, "RIGHT_WRIST": 16, "LEFT_HIP": 23, "RIGHT_HIP": 24, "LEFT_KNEE": 25,
         "RIGHT_KNEE": 26, "LEFT_ANKLE": 27, "RIGHT_ANKLE": 28, "LEFT_HEEL": 29, "RIGHT_HEEL": 30,
         "LEFT_FOOT_INDEX": 31, "RIGHT_FOOT_INDEX": 32}
LEGS = (("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE", "LEFT_HEEL", "LEFT_FOOT_INDEX"),
        ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE", "RIGHT_HEEL", "RIGHT_FOOT_INDEX"))


def _ok(f: np.ndarray, *names: str) -> bool:
    return all(f[JOINT[n], 3] >= MIN_VIS and np.isfinite(f[JOINT[n], :3]).all() for n in names)


def _p(f: np.ndarray, name: str) -> np.ndarray:
    return f[JOINT[name], :2]


def _deviation(series: list[float | None], wrap: bool = False) -> tuple[float, float]:
    """(max, mean) absolute deviation from the starting value; zeros when too little valid data."""
    vals = [v for v in series if v is not None]
    if len(vals) < 3:
        return 0.0, 0.0
    base = float(np.median(vals[:5]))
    devs = []
    for v in vals:
        d = v - base
        if wrap:
            d = (d + 180.0) % 360.0 - 180.0
        devs.append(abs(d))
    return max(devs), float(np.mean(devs))


def _torso(f: np.ndarray) -> tuple[np.ndarray, float] | None:
    if not _ok(f, "LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP"):
        return None
    d = (_p(f, "LEFT_SHOULDER") + _p(f, "RIGHT_SHOULDER")) / 2 - (_p(f, "LEFT_HIP") + _p(f, "RIGHT_HIP")) / 2
    n = float(np.hypot(*d))
    return (d, n) if n > 1e-6 else None


def _series_angles(arr: np.ndarray, names: list[str], use_z: bool) -> list[float | None]:
    out = []
    for f in arr:
        lm = [Landmark(*map(float, f[JOINT[n]])) for n in names]
        out.append(joint_angle(*lm, min_conf=MIN_VIS, use_z=use_z))
    return out


def _mirror(names: list[str]) -> list[str]:
    return [n.replace("LEFT_", "@").replace("RIGHT_", "LEFT_").replace("@", "RIGHT_") for n in names]


POSTURE_ZEROS = {
    "torso_tilt_dev_max": 0.0, "torso_tilt_dev_mean": 0.0, "shoulder_asym_dev_max": 0.0, "head_tilt_dev_max": 0.0,
    "elbow_bend_min_deg": 180.0, "elbow_bend_min_3d_deg": 180.0, "lr_angle_asym_mean_deg": 0.0, "rom3d_deg": 0.0,
    "peak3d_minus_2d_progress": 0.0, "knee_valgus_dev_max": 0.0, "heel_lift_dev_max": 0.0,
    "knee_over_toe_dev_max": 0.0, "lower_body_exercise": 0.0, "posture_reliability": 0.0,
}


def posture_features(a2d: np.ndarray, a3d: np.ndarray | None, ex: Exercise, side: str) -> dict[str, float]:
    out = dict(POSTURE_ZEROS)
    if len(a2d) == 0:
        return out
    out["lower_body_exercise"] = 1.0 if "knee" in ex.target_joints else 0.0

    torso = [_torso(f) for f in a2d]
    out["posture_reliability"] = sum(t is not None for t in torso) / len(torso)
    tilt = [math.degrees(math.atan2(t[0][0], -t[0][1])) if t else None for t in torso]
    out["torso_tilt_dev_max"], out["torso_tilt_dev_mean"] = _deviation(tilt, wrap=True)

    asym = []
    for f, t in zip(a2d, torso):
        asym.append(float((_p(f, "LEFT_SHOULDER")[1] - _p(f, "RIGHT_SHOULDER")[1]) / t[1]) if t else None)
    out["shoulder_asym_dev_max"], _ = _deviation(asym)

    head = [math.degrees(math.atan2(*(_p(f, "RIGHT_EAR") - _p(f, "LEFT_EAR"))[::-1])) if _ok(f, "LEFT_EAR", "RIGHT_EAR") else None
            for f in a2d]
    out["head_tilt_dev_max"], _ = _deviation(head, wrap=True)

    valg, heel, toe = [], [], []
    for hip, knee, ankle, hl, ft in LEGS:
        v, h, k = [], [], []
        for f in a2d:
            if _ok(f, hip, knee, ankle):
                a, b, c = _p(f, hip), _p(f, knee), _p(f, ankle)
                leg = float(np.hypot(*(c - a)))
                if leg > 1e-6:
                    v.append(abs(float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))) / leg / leg)
                    h.append(float((_p(f, ft)[1] - _p(f, hl)[1]) / leg) if _ok(f, hl, ft) else None)
                    k.append(abs(float(b[0] - _p(f, ft)[0])) / leg if _ok(f, ft) else None)
                    continue
            v.append(None); h.append(None); k.append(None)
        valg.append(_deviation(v)[0]); heel.append(_deviation(h)[0]); toe.append(_deviation(k)[0])
    out["knee_valgus_dev_max"], out["heel_lift_dev_max"], out["knee_over_toe_dev_max"] = max(valg), max(heel), max(toe)

    elbow = [f"{side}_SHOULDER", f"{side}_ELBOW", f"{side}_WRIST"]
    e2 = [a for a in _series_angles(a2d, elbow, False) if a is not None]
    out["elbow_bend_min_deg"] = min(e2) if e2 else 180.0

    names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
    a_main = _series_angles(a2d, names, False)
    a_mirror = _series_angles(a2d, _mirror(names), False)
    pairs = [abs(x - y) for x, y in zip(a_main, a_mirror) if x is not None and y is not None]
    out["lr_angle_asym_mean_deg"] = float(np.mean(pairs)) if pairs else 0.0

    if a3d is not None and len(a3d) == len(a2d):
        a3 = [a for a in _series_angles(a3d, names, True) if a is not None]
        span = ex.target_angle_deg - ex.start_angle_deg
        v2 = [a for a in a_main if a is not None]
        if a3 and v2:
            out["rom3d_deg"] = max(a3) - min(a3)
            out["peak3d_minus_2d_progress"] = max((a - ex.start_angle_deg) / span for a in a3) \
                - max((a - ex.start_angle_deg) / span for a in v2)
        e3 = [a for a in _series_angles(a3d, elbow, True) if a is not None]
        out["elbow_bend_min_3d_deg"] = min(e3) if e3 else 180.0
    return out
