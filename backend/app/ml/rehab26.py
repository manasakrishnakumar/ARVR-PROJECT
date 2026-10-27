"""Importer for REHAB26-ViewAngles (Zenodo 10.5281/zenodo.23018128, CC BY-NC 4.0; cite the dataset authors).

Healthy volunteers deliberately performing correct and incorrect repetitions, filmed by 3 phones, with
MediaPipe Pose skeletons. Each repetition is turned into one dataset row using one camera (the most
informative view for that exercise). Raw data is NOT redistributed here: keep it out of git.
"""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.angle_calculation.angles import AngleSmoother, Landmark, joint_angle
from app.exercises.library import get_exercise
from app.feature_extraction.features import rep_features
from app.ml.dataset import Row
from app.repetition_detection.counter import Repetition

FPS = 30.0
SOURCE = "rehab26-zenodo-23018128 (CC BY-NC 4.0)"
# dataset exercise id -> (our exercise id, body side measured, preferred |viewing angle| in degrees)
EXERCISES = {"1": ("shoulder_abduction", "RIGHT", 0), "6": ("sit_to_stand", "LEFT", 90)}
RANGE_ERRORS = {"ERR_LOW_ABDUCTION", "ERR_SHALLOW_SQUAT"}  # the only errors our range feature can express
JOINT = {"LEFT_SHOULDER": 11, "RIGHT_SHOULDER": 12, "LEFT_ELBOW": 13, "RIGHT_ELBOW": 14, "LEFT_HIP": 23,
         "RIGHT_HIP": 24, "LEFT_KNEE": 25, "RIGHT_KNEE": 26, "LEFT_ANKLE": 27, "RIGHT_ANKLE": 28}


def map_label(correctness: str, error_code: str) -> str:
    if correctness == "1":
        return "acceptable"
    return "insufficient_range" if error_code in RANGE_ERRORS else "posture_deviation"


def choose_camera(orientation_deg: int, preferred_abs_view: int) -> int:
    """Viewing angle of cam1/2/3 is -o, 45-o, 90-o (0 = frontal, +/-90 = profile)."""
    views = {1: -orientation_deg, 2: 45 - orientation_deg, 3: 90 - orientation_deg}
    return min(views, key=lambda c: abs(abs(views[c]) - preferred_abs_view))


def _landmarks(frame: np.ndarray, names: list[str]) -> list[Landmark]:
    out = []
    for n in names:
        x, y, z, v = frame[JOINT[n]]
        out.append(Landmark(float(x), float(y), float(z), float(v)))
    return out


def import_rehab26(root: Path, min_conf: float = 0.5) -> tuple[list[Row], dict]:
    """root contains Segmentation.csv and mediapipe/<exN>/<video_id>_cam<k>_2d.npy"""
    with (root / "Segmentation.csv").open(encoding="utf-8", newline="") as f:
        seg = list(csv.DictReader(f, delimiter=";"))
    stats = defaultdict(int)
    jobs: dict[Path, list[dict]] = defaultdict(list)
    for r in seg:
        if r["exercise_id"] not in EXERCISES:
            stats["skipped_exercise_not_supported"] += 1
            continue
        _, _, view = EXERCISES[r["exercise_id"]]
        cam = choose_camera(int(r["person_orientation"]), view)
        r["_cam"] = cam
        jobs[root / "mediapipe" / f"ex{r['exercise_id']}" / f"{r['video_id']}_cam{cam}_2d.npy"].append(r)

    rows: list[Row] = []
    for path, reps in jobs.items():
        if not path.exists():
            stats["skipped_missing_file"] += len(reps)
            continue
        arr = np.load(path, allow_pickle=False)  # never unpickle downloaded data
        for r in reps:
            ex_id, side, _ = EXERCISES[r["exercise_id"]]
            ex = get_exercise(ex_id)
            if ex is None:
                stats["skipped_unknown_exercise"] += 1
                continue
            names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
            first, last = int(r["first_frame"]), min(int(r["last_frame"]), len(arr) - 1)
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
            rows.append({"participant_id": r["person"], "recording_id": f"{r['video_id']}-r{r['repetition_number']}",
                         "exercise_id": ex_id, "label": label, "source": SOURCE, **rep_features(rep),
                         "camera": r["_cam"], "orientation_deg": r["person_orientation"],
                         "error_code": r["error_description"]})
            stats["imported"] += 1
    return rows, dict(stats)
