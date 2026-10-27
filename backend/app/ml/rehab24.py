"""Importer for REHAB24-6 (Zenodo 10.5281/zenodo.13305826, CC BY-NC 4.0; cite the dataset authors).

Skeletons come from an optical motion-capture system (26 joints, projected to the two RGB cameras, pixel coordinates),
NOT from a pose estimator, and there are no per-joint confidences. Joints are mapped onto the MediaPipe landmark
layout so the same feature code can be reused; landmarks the mocap skeleton lacks (ears, heels) are marked invisible.
Labels are binary (correct / incorrect) with no error type. Raw data is NOT redistributed here: keep it out of git.
"""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.angle_calculation.angles import AngleSmoother, joint_angle
from app.exercises.library import get_exercise
from app.feature_extraction.features import rep_features
from app.feature_extraction.posture import posture_features
from app.ml.dataset import Row
from app.ml.rehab26 import _landmarks
from app.repetition_detection.counter import Repetition

FPS = 30.0
SOURCE = "rehab24-6-zenodo-13305826 (CC BY-NC 4.0)"
SOURCE_VIDEO = "rehab24-6-videos-mediapipe-full (CC BY-NC 4.0)"
ZENODO_VIDEOS_URL = "https://zenodo.org/records/13305826/files/videos.zip?download=1"
# dataset exercise id -> (our exercise id, side, preferred |viewing angle|, folder)
EXERCISES = {"1": ("shoulder_abduction", "RIGHT", 0), "6": ("sit_to_stand", "LEFT", 90)}
VIEW_DEG = {"front": 0, "half-profile": 45, "profile": 90}
CAM18_VIEW = {"front": "profile", "half-profile": "half-profile", "profile": "front"}  # cam18 is orthogonal to cam17
# MediaPipe landmark index <- mocap joint index (see joints_names.txt)
MOCAP_TO_MP = {11: 7, 12: 12, 13: 8, 14: 13, 15: 9, 16: 14, 23: 16, 24: 21, 25: 17, 26: 22, 27: 18, 28: 23,
               31: 20, 32: 25}


def to_mediapipe_layout(mocap: np.ndarray) -> np.ndarray:
    """(T, 26, 2) pixel coordinates -> (T, 33, 4) array; unmapped landmarks get visibility 0."""
    out = np.zeros((len(mocap), 33, 4))
    for mp, mc in MOCAP_TO_MP.items():
        out[:, mp, :2] = mocap[:, mc, :]
        out[:, mp, 3] = 1.0
    return out


def choose_camera(cam17_orientation: str, preferred_abs_view: int) -> int:
    v17 = VIEW_DEG[cam17_orientation]
    v18 = VIEW_DEG[CAM18_VIEW[cam17_orientation]]
    return 17 if abs(v17 - preferred_abs_view) <= abs(v18 - preferred_abs_view) else 18


def needed_recordings(root: Path) -> dict[tuple[str, str, int], list[tuple[int, int]]]:
    """(exercise id, video id, camera) -> repetition frame ranges, for the repetitions the importer would use."""
    with (root / "Segmentation.csv").open(encoding="utf-8", newline="") as f:
        seg = list(csv.DictReader(f, delimiter=";"))
    need: dict[tuple[str, str, int], list[tuple[int, int]]] = defaultdict(list)
    for r in seg:
        if r["exercise_id"] in EXERCISES and r["mocap_erroneous"] != "1":
            cam = choose_camera(r["cam17_orientation"], EXERCISES[r["exercise_id"]][2])
            need[(r["exercise_id"], r["video_id"], cam)].append((int(r["first_frame"]), int(r["last_frame"])))
    return dict(need)


def video_entry_name(entries: dict[str, int], exd: str, video: str, cam: int) -> str | None:
    """Zip entry for a recording (camera 18 files carry a '-transposed' suffix)."""
    prefix = f"Ex{exd}/{video}-Camera{cam}-30fps"
    return next((n for n in entries if n.startswith(prefix) and n.endswith(".mp4")), None)


def import_rehab24_video(root: Path, min_conf: float = 0.5) -> tuple[list[Row], dict]:
    """Rows from MediaPipe Pose run on the REHAB24-6 videos (see `extract-rehab24-videos`): same estimator family and
    feature code as REHAB26, including 3D and ear/heel based features. Same 369 repetitions as the mocap import."""
    import json

    from app.ml.rehab26 import build_rep_row

    with (root / "Segmentation.csv").open(encoding="utf-8", newline="") as f:
        seg = list(csv.DictReader(f, delimiter=";"))
    stats: dict[str, int] = defaultdict(int)
    groups: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for r in seg:
        if r["exercise_id"] not in EXERCISES:
            stats["skipped_exercise_not_supported"] += 1
        elif r["mocap_erroneous"] == "1":
            stats["skipped_mocap_erroneous"] += 1  # kept out so both REHAB24-6 variants use the same repetitions
        else:
            groups[(r["exercise_id"], r["video_id"], choose_camera(r["cam17_orientation"], EXERCISES[r["exercise_id"]][2]))].append(r)
    rows: list[Row] = []
    for (exd, video, cam), reps in groups.items():
        base = root / "mediapipe" / f"Ex{exd}" / f"{video}-c{cam}"
        meta_path = base.with_name(base.name + "_meta.json")
        if not meta_path.exists():
            stats["skipped_not_extracted"] += len(reps)
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        arr = np.load(base.with_name(base.name + "_2d.npy"), allow_pickle=False).astype(np.float64)
        arr3d = np.load(base.with_name(base.name + "_3d.npy"), allow_pickle=False).astype(np.float64)
        arr[:, :, 0] *= meta["width"] / meta["height"]  # equalise the x and y scales (frames were stored upright)
        ex_id, side, _ = EXERCISES[exd]
        ex = get_exercise(ex_id)
        assert ex is not None
        for r in reps:
            row = build_rep_row(arr, arr3d, ex, side, int(r["first_frame"]), int(r["last_frame"]),
                                int(r["repetition_number"]), min_conf, {
                "participant_id": f"P{r['person_id']}", "recording_id": f"{video}-r{r['repetition_number']}",
                "exercise_id": ex_id, "label": "acceptable" if r["correctness"] == "1" else "incorrect_unspecified",
                "source": SOURCE_VIDEO, "camera": cam, "orientation_deg": r["cam17_orientation"], "error_code": ""})
            if row is None:
                stats["skipped_too_few_valid_frames"] += 1
                continue
            rows.append(row)
            stats["imported"] += 1
    return rows, dict(stats)


def import_rehab24(root: Path, min_conf: float = 0.5) -> tuple[list[Row], dict]:
    """root contains Segmentation.csv and Ex<N>/<video_id>-c17|c18-30fps.npy"""
    with (root / "Segmentation.csv").open(encoding="utf-8", newline="") as f:
        seg = list(csv.DictReader(f, delimiter=";"))
    stats: dict[str, int] = defaultdict(int)
    groups: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for r in seg:
        if r["exercise_id"] not in EXERCISES:
            stats["skipped_exercise_not_supported"] += 1
            continue
        if r["mocap_erroneous"] == "1":
            stats["skipped_mocap_erroneous"] += 1
            continue
        cam = choose_camera(r["cam17_orientation"], EXERCISES[r["exercise_id"]][2])
        groups[(r["exercise_id"], r["video_id"], cam)].append(r)

    rows: list[Row] = []
    for (exd, video, cam), reps in groups.items():
        path = root / f"Ex{exd}" / f"{video}-c{cam}-30fps.npy"
        if not path.exists():
            stats["skipped_missing_file"] += len(reps)
            continue
        arr = to_mediapipe_layout(np.load(path, allow_pickle=False))  # never unpickle downloaded data
        ex_id, side, _ = EXERCISES[exd]
        ex = get_exercise(ex_id)
        assert ex is not None
        names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
        for r in reps:
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
            post = posture_features(arr[first:last + 1], None, ex, side)  # no 3D features for mocap joints
            rows.append({"participant_id": f"P{r['person_id']}", "recording_id": f"{video}-r{r['repetition_number']}",
                         "exercise_id": ex_id, "label": "acceptable" if r["correctness"] == "1" else "incorrect_unspecified",
                         "source": SOURCE, **rep_features(rep), **post, "camera": cam,
                         "orientation_deg": r["cam17_orientation"], "error_code": ""})
            stats["imported"] += 1
    return rows, dict(stats)
