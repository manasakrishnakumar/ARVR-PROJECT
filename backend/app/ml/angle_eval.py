"""Angle estimation accuracy: MediaPipe joint angles versus optical motion-capture joint angles (REHAB24-6).

The same frames of each recording are measured twice: by MediaPipe Pose run on the video, and by the dataset's motion-capture
skeleton projected into the same camera image. Both use the exercise's three landmarks in the image plane (2D, isotropic
pixel units). Caveats: motion capture is a reference, not ground truth: its joint centres are defined differently from
MediaPipe's landmarks (e.g. glenohumeral vs a surface-based shoulder), so part of the difference is definitional, and
frame alignment between the two sources is checked rather than assumed (see best_lag).
"""
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.angle_calculation.angles import joint_angle
from app.exercises.library import Exercise, get_exercise
from app.ml.rehab26 import _landmarks

LAGS = range(-8, 9)


def paired_angles(mp: np.ndarray, ref: np.ndarray, names: list[str], frames: list[int], lag: int = 0) -> list[tuple[float, float]]:
    """(estimated, reference) angle pairs; the reference frame is shifted by `lag` frames. Frames lacking either angle are dropped."""
    out = []
    for f in frames:
        g = f + lag
        if not 0 <= g < len(ref):
            continue
        a = joint_angle(*_landmarks(mp[f], names), min_conf=0.5)
        b = joint_angle(*_landmarks(ref[g], names), min_conf=0.5)
        if a is not None and b is not None:
            out.append((a, b))
    return out


def error_metrics(pairs: list[tuple[float, float]]) -> dict:
    if len(pairs) < 3:
        return {"n": len(pairs), "mae_deg": None, "rmse_deg": None, "bias_deg": None, "loa95_deg": None, "pearson_r": None}
    est, ref = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    d = est - ref
    sd = float(d.std(ddof=1))
    r = float(np.corrcoef(est, ref)[0, 1]) if est.std() > 0 and ref.std() > 0 else None
    return {"n": len(pairs), "mae_deg": float(np.abs(d).mean()), "rmse_deg": float(math.sqrt((d ** 2).mean())),
            "bias_deg": float(d.mean()), "loa95_deg": [float(d.mean() - 1.96 * sd), float(d.mean() + 1.96 * sd)], "pearson_r": r}


def best_lag(mp: np.ndarray, ref: np.ndarray, names: list[str], frames: list[int]) -> tuple[int, dict[int, float]]:
    """Lag (frames) at which the two sources agree best: a check on frame alignment, not a fitted correction."""
    maes = {}
    for lag in LAGS:
        pairs = paired_angles(mp, ref, names, frames, lag)
        if len(pairs) >= 10:
            maes[lag] = float(np.mean([abs(a - b) for a, b in pairs]))
    return (min(maes, key=maes.get) if maes else 0), maes  # type: ignore[arg-type]


def evaluate_rehab24(root: Path) -> dict:
    from app.ml.rehab24 import EXERCISES, needed_recordings, to_mediapipe_layout

    pooled: list[tuple[float, float]] = []
    by_ex: dict[str, list] = defaultdict(list)
    by_cam: dict[int, list] = defaultdict(list)
    lags: list[int] = []
    n_rec = skipped = 0
    for (exd, video, cam) in needed_recordings(root):
        base = root / "mediapipe" / f"Ex{exd}" / f"{video}-c{cam}"
        meta_p = base.with_name(base.name + "_meta.json")
        mocap_p = root / f"Ex{exd}" / f"{video}-c{cam}-30fps.npy"
        if not meta_p.exists() or not mocap_p.exists():
            skipped += 1
            continue
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        mp = np.load(base.with_name(base.name + "_2d.npy"), allow_pickle=False).astype(np.float64)
        mp[:, :, 0] *= meta["width"]  # normalised -> pixels (x by width, y by height)
        mp[:, :, 1] *= meta["height"]
        ref = to_mediapipe_layout(np.load(mocap_p, allow_pickle=False))
        ex_id, side, _ = EXERCISES[exd]
        ex = get_exercise(ex_id)
        assert ex is not None
        names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
        frames = [f for f in range(min(len(mp), len(ref))) if mp[f, :, 3].any()]
        if len(frames) < 30:
            skipped += 1
            continue
        lag, _ = best_lag(mp, ref, names, frames)
        lags.append(lag)
        pairs = paired_angles(mp, ref, names, frames, 0)
        pooled += pairs
        by_ex[ex_id] += pairs
        by_cam[cam] += pairs
        n_rec += 1
    return {
        "recordings": n_rec, "recordings_skipped": skipped, "overall": error_metrics(pooled),
        "by_exercise": {k: error_metrics(v) for k, v in by_ex.items()},
        "by_camera": {f"cam{k}": error_metrics(v) for k, v in by_cam.items()},
        "best_lag_frames_median": statistics.median(lags) if lags else None,
        "best_lag_frames_all_zero_fraction": (sum(1 for x in lags if x == 0) / len(lags)) if lags else None,
        "note": "Reference = optical motion capture projected to the camera image; definitional differences between mocap "
                "joint centres and MediaPipe landmarks are part of the error. 2D image-plane angles only.",
    }
