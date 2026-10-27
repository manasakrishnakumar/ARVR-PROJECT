"""Repetition-counting evaluation against the datasets' labelled repetition boundaries.

The live counter needs a start and a target angle. Two ways of setting them are compared on real recordings:
  illustrative  - the exercise definition's illustrative angles (what the app uses today)
  auto          - calibrated from the recording itself: start/target = 10th/90th percentile of the measured angle
                  (no labels used; this is what a short calibration phase in the app could do)
Counting is evaluated two ways: attempts (every excursion, matched to labelled repetitions by overlap) and counts
(number of detected repetitions vs number labelled).
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.angle_calculation.angles import AngleSmoother, joint_angle
from app.exercises.library import Exercise, get_exercise
from app.ml.rehab26 import FPS, _landmarks
from app.repetition_detection.counter import RepConfig, RepetitionCounter

MARGIN = 15  # frames of rest kept either side of a block
IOU_MATCH = 0.5


def angle_series(arr: np.ndarray, names: list[str], min_conf: float = 0.5) -> list[float | None]:
    return [joint_angle(*_landmarks(f, names), min_conf=min_conf) for f in arr]


def auto_range(angles: list[float | None], ex: Exercise) -> tuple[float, float] | None:
    """Start/target estimated from the data: percentiles of the smoothed angle, in the exercise's movement direction."""
    sm, vals = AngleSmoother(), []
    for a in angles:
        s = sm.update(a) if a is not None else None
        if s is not None:
            vals.append(s)
    if len(vals) < 30:
        return None
    lo, hi = float(np.percentile(vals, 10)), float(np.percentile(vals, 90))
    if hi - lo < 15:  # almost no movement: cannot calibrate
        return None
    return (lo, hi) if ex.target_angle_deg > ex.start_angle_deg else (hi, lo)


def detect(angles: list[float | None], start: float, target: float, required_fraction: float, hysteresis_deg: float,
           fps: float = FPS) -> list[tuple[int, int, bool]]:
    """Run the live counter over a series. Returns (first_frame, last_frame, reached_target) per detected excursion."""
    counter = RepetitionCounter(RepConfig(start_angle=start, target_angle=target, required_fraction=required_fraction,
                                          hysteresis_deg=hysteresis_deg))
    sm, out = AngleSmoother(), []
    for i, a in enumerate(angles):
        rep = counter.update(i / fps, sm.update(a) if a is not None else None)
        if rep is not None:
            out.append((round(rep.t_start * fps), round(rep.t_end * fps), rep.reached_target))
    return out


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def match(truth: list[tuple[int, int]], found: list[tuple[int, int]], thr: float = IOU_MATCH) -> int:
    """Number of one-to-one matches between detected and labelled intervals (greedy by overlap)."""
    pairs = sorted(((_iou(t, f), i, j) for i, t in enumerate(truth) for j, f in enumerate(found)), reverse=True)
    used_t, used_f, tp = set(), set(), 0
    for iou, i, j in pairs:
        if iou < thr:
            break
        if i not in used_t and j not in used_f:
            used_t.add(i); used_f.add(j); tp += 1
    return tp


class Block:
    """One stretch of a recording with labelled repetitions: its angle series and the labelled intervals."""
    def __init__(self, dataset: str, exercise: Exercise, angles: list[float | None], offset: int, truth: list[tuple[int, int]]):
        self.dataset, self.exercise, self.angles, self.offset, self.truth = dataset, exercise, angles, offset, truth


def evaluate_blocks(blocks: list[Block], required_fraction: float = 0.6) -> dict:
    """required_fraction 0.6 is the level-1 range requirement of the exercise definitions."""
    res: dict = {}
    for mode in ("illustrative", "auto"):
        n_blocks = n_truth = n_found = n_tp = skipped = exact = 0
        errs: list[int] = []
        by_ex: dict[str, list[int]] = defaultdict(list)
        for b in blocks:
            if mode == "illustrative":
                start, target = b.exercise.start_angle_deg, b.exercise.target_angle_deg
            else:
                rng = auto_range(b.angles, b.exercise)
                if rng is None:
                    skipped += 1
                    continue
                start, target = rng
            hyst = b.exercise.hysteresis_deg if mode == "illustrative" else 0.1 * abs(target - start)
            found = [(a, z) for a, z, _ in detect(b.angles, start, target, required_fraction, hyst)]  # relative to the block
            tp = match([(a - b.offset, z - b.offset) for a, z in b.truth], found)
            err = abs(len(found) - len(b.truth))
            n_blocks += 1; n_truth += len(b.truth); n_found += len(found); n_tp += tp; errs.append(err)
            exact += err == 0
            by_ex[b.exercise.id].append(err)
        prec = n_tp / n_found if n_found else 0.0
        rec = n_tp / n_truth if n_truth else 0.0
        res[mode] = {
            "blocks": n_blocks, "blocks_skipped_no_calibration": skipped, "labelled_repetitions": n_truth,
            "detected_repetitions": n_found, "matched": n_tp,
            "mean_absolute_count_error": statistics.fmean(errs) if errs else None,
            "exact_count_fraction": exact / n_blocks if n_blocks else None,
            "precision": prec, "recall": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "mean_absolute_count_error_by_exercise": {k: statistics.fmean(v) for k, v in by_ex.items()},
        }
    return res


# ---- dataset loaders (raw data stays local) ---------------------------------------------------------------------

def blocks_rehab26(root: Path, aspect: float = 0.5625) -> list[Block]:
    from app.ml.rehab26 import EXERCISES, _visible_fraction, choose_camera

    rows = list(csv.DictReader((root / "Segmentation.csv").open(encoding="utf-8", newline=""), delimiter=";"))
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in rows:
        if r["exercise_id"] in EXERCISES:
            groups[(r["exercise_id"], r["video_id"], r["person_orientation"])].append(r)
    cache: dict[Path, np.ndarray] = {}
    blocks = []
    for (exd, video, orient), reps in groups.items():
        ex_id, side, view = EXERCISES[exd]
        ex = get_exercise(ex_id)
        if ex is None:
            continue
        names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
        first, last = min(int(r["first_frame"]) for r in reps), max(int(r["last_frame"]) for r in reps)
        arrs = {}
        for cam in (1, 2, 3):
            p = root / "mediapipe" / f"ex{exd}" / f"{video}_cam{cam}_2d.npy"
            if p.exists():
                if p not in cache:
                    a = np.load(p, allow_pickle=False).copy()
                    a[:, :, 0] *= aspect
                    cache[p] = a
                arrs[cam] = cache[p]
        if not arrs:
            continue
        vis = {c: _visible_fraction(a, names, first, min(last, len(a) - 1), 0.5) for c, a in arrs.items()}
        arr = arrs[choose_camera(int(orient), view, vis)]
        lo, hi = max(0, first - MARGIN), min(len(arr), last + MARGIN + 1)
        blocks.append(Block("rehab26", ex, angle_series(arr[lo:hi], names), lo,
                            [(int(r["first_frame"]), int(r["last_frame"])) for r in reps]))
        if len(cache) > 6:
            cache.clear()
    return blocks


def blocks_rehab24_mocap(root: Path) -> list[Block]:
    from app.ml.rehab24 import EXERCISES, choose_camera, to_mediapipe_layout

    rows = list(csv.DictReader((root / "Segmentation.csv").open(encoding="utf-8", newline=""), delimiter=";"))
    groups: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for r in rows:
        if r["exercise_id"] in EXERCISES and r["mocap_erroneous"] != "1":
            groups[(r["exercise_id"], r["video_id"], choose_camera(r["cam17_orientation"], EXERCISES[r["exercise_id"]][2]))].append(r)
    blocks = []
    for (exd, video, cam), reps in groups.items():
        ex_id, side, _ = EXERCISES[exd]
        ex = get_exercise(ex_id)
        path = root / f"Ex{exd}" / f"{video}-c{cam}-30fps.npy"
        if ex is None or not path.exists():
            continue
        arr = to_mediapipe_layout(np.load(path, allow_pickle=False))
        names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
        first, last = min(int(r["first_frame"]) for r in reps), max(int(r["last_frame"]) for r in reps)
        lo, hi = max(0, first - MARGIN), min(len(arr), last + MARGIN + 1)
        blocks.append(Block("rehab24-mocap", ex, angle_series(arr[lo:hi], names), lo,
                            [(int(r["first_frame"]), int(r["last_frame"])) for r in reps]))
    return blocks
