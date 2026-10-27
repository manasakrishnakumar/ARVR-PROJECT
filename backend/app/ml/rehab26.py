"""Importer for REHAB26-ViewAngles (Zenodo 10.5281/zenodo.23018128, CC BY-NC 4.0; cite the dataset authors).

Healthy volunteers deliberately performing correct and incorrect repetitions, filmed by 3 phones, with
MediaPipe Pose skeletons. Each repetition is turned into one dataset row using one camera. Raw data is NOT
redistributed here: keep it out of git.
"""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.angle_calculation.angles import AngleSmoother, Landmark, joint_angle
from app.exercises.library import get_exercise
from app.feature_extraction.features import rep_features
from app.feature_extraction.posture import posture_features
from app.ml.dataset import Row
from app.repetition_detection.counter import Repetition

FPS = 30.0
SOURCE = "rehab26-zenodo-23018128 (CC BY-NC 4.0)"
# dataset exercise id -> (our exercise id, body side measured, preferred |viewing angle| in degrees)
EXERCISES = {"1": ("shoulder_abduction", "RIGHT", 0), "6": ("sit_to_stand", "LEFT", 90),
             "7": ("shoulder_extension", "RIGHT", 90)}
RANGE_ERRORS = {"ERR_LOW_ABDUCTION", "ERR_SHALLOW_SQUAT"}  # the only errors our range feature can express
# (shoulder extension has no range-type error code, so all its errors are posture deviations)
VISIBLE_ENOUGH = 0.8  # a camera is usable if the exercise's joints are visible in at least this fraction of frames
JOINT = {"LEFT_SHOULDER": 11, "RIGHT_SHOULDER": 12, "LEFT_ELBOW": 13, "RIGHT_ELBOW": 14, "LEFT_HIP": 23,
         "RIGHT_HIP": 24, "LEFT_KNEE": 25, "RIGHT_KNEE": 26, "LEFT_ANKLE": 27, "RIGHT_ANKLE": 28}


def map_label(correctness: str, error_code: str) -> str:
    if correctness == "1":
        return "acceptable"
    return "insufficient_range" if error_code in RANGE_ERRORS else "posture_deviation"


def viewing_angles(orientation_deg: int) -> dict[int, int]:
    """Viewing angle of cam1/2/3 is -o, 45-o, 90-o (0 = frontal, +/-90 = profile)."""
    return {1: -orientation_deg, 2: 45 - orientation_deg, 3: 90 - orientation_deg}


def choose_camera(orientation_deg: int, preferred_abs_view: int, visibility: dict[int, float] | None = None) -> int:
    """Camera whose view is closest to the preferred one among cameras that see the exercise's joints.

    Uses only geometry and landmark visibility (never labels). If no camera reaches VISIBLE_ENOUGH, the
    most visible one is used."""
    views = viewing_angles(orientation_deg)
    order = sorted(views, key=lambda c: abs(abs(views[c]) - preferred_abs_view))
    if visibility is None:
        return order[0]
    usable = [c for c in order if c in visibility and visibility[c] >= VISIBLE_ENOUGH]
    if usable:
        return usable[0]
    return max(visibility, key=visibility.get)  # type: ignore[arg-type]


def _landmarks(frame: np.ndarray, names: list[str]) -> list[Landmark]:
    out = []
    for n in names:
        x, y, z, v = frame[JOINT[n]]
        out.append(Landmark(float(x), float(y), float(z), float(v)))
    return out


def _visible_fraction(arr: np.ndarray, names: list[str], first: int, last: int, min_conf: float) -> float:
    seg = arr[first:last + 1][:, [JOINT[n] for n in names], 3]
    return float((seg >= min_conf).all(axis=1).mean()) if len(seg) else 0.0


def import_rehab26(root: Path, min_conf: float = 0.5, aspect: float = 1.0) -> tuple[list[Row], dict]:
    """root contains Segmentation.csv and mediapipe/<exN>/<video_id>_cam<k>_2d.npy

    aspect = video width / height. 2D coordinates are normalised separately per axis, so x is multiplied by the
    aspect ratio to make both axes the same scale (otherwise angles are distorted). The videos were not downloaded:
    the portrait 9:16 value (0.5625) is inferred from comparing 2D and 3D skeleton scales (median estimate 0.53)."""
    with (root / "Segmentation.csv").open(encoding="utf-8", newline="") as f:
        seg = list(csv.DictReader(f, delimiter=";"))
    stats: dict[str, int] = defaultdict(int)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in seg:
        if r["exercise_id"] not in EXERCISES:
            stats["skipped_exercise_not_supported"] += 1
            continue
        groups[(r["exercise_id"], r["video_id"])].append(r)

    rows: list[Row] = []
    for (exd, video), reps in groups.items():
        folder = root / "mediapipe" / f"ex{exd}"
        arrs: dict[int, np.ndarray] = {}
        for cam in (1, 2, 3):
            p = folder / f"{video}_cam{cam}_2d.npy"
            if p.exists():
                a = np.load(p, allow_pickle=False)  # never unpickle downloaded data
                if aspect != 1.0:
                    a = a.copy()
                    a[:, :, 0] *= aspect
                arrs[cam] = a
        if not arrs:
            stats["skipped_missing_file"] += len(reps)
            continue
        arrs3d: dict[int, np.ndarray | None] = {}
        for r in reps:
            ex_id, side, view = EXERCISES[exd]
            ex = get_exercise(ex_id)
            if ex is None:
                stats["skipped_unknown_exercise"] += 1
                continue
            names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
            first, last_req = int(r["first_frame"]), int(r["last_frame"])
            vis = {c: _visible_fraction(a, names, first, min(last_req, len(a) - 1), min_conf) for c, a in arrs.items()}
            cam = choose_camera(int(r["person_orientation"]), view, vis)
            arr = arrs[cam]
            if cam not in arrs3d:
                p3 = folder / f"{video}_cam{cam}_3d.npy"
                arrs3d[cam] = np.load(p3, allow_pickle=False) if p3.exists() else None
            arr3d = arrs3d[cam]
            if arr3d is None:
                stats["missing_3d_file"] += 1
            last = min(last_req, len(arr) - 1)
            sm, times, angles, missing = AngleSmoother(), [], [], 0
            for fr in range(first, last + 1):
                a = joint_angle(*_landmarks(arr[fr], names), min_conf=min_conf)
                if a is None:
                    missing += 1
                    continue
                times.append(fr / FPS)
                angles.append(sm.update(a))
            n_frames = last - first + 1
            if len(angles) < 5 or n_frames < 5:
                stats["skipped_too_few_valid_frames"] += 1
                continue
            span = ex.target_angle_deg - ex.start_angle_deg
            peak = max((a - ex.start_angle_deg) / span for a in angles)
            rep = Repetition(index=int(r["repetition_number"]), t_start=times[0], t_end=times[-1], peak_progress=peak,
                             times=times, angles=angles, n_frames=n_frames, n_missing=missing, reached_target=False)
            label = map_label(r["correctness_score"], r["error_description"])
            seg3d = arr3d[first:last + 1] if arr3d is not None and len(arr3d) == len(arr) else None
            post = posture_features(arr[first:last + 1], seg3d, ex, side)
            rows.append({"participant_id": r["person"], "recording_id": f"{r['video_id']}-r{r['repetition_number']}",
                         "exercise_id": ex_id, "label": label, "source": SOURCE, **rep_features(rep), **post,
                         "camera": cam, "orientation_deg": r["person_orientation"], "error_code": r["error_description"]})
            stats["imported"] += 1
    return rows, dict(stats)
