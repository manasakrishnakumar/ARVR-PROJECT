"""Validation of the Unity on-device pose feature (BlazePose run by Unity's Inference Engine) against optical motion capture (REHAB24-6).

Method, the same as angle_eval.py (MediaPipe Python vs motion capture) so the numbers are comparable:
  * Frames of each recording were extracted (every 3rd frame, downscaled to 640 px wide, like a webcam) and run through the Unity
    pipeline in order by `Arvr.Editor.ValidatePose` (tracking carries over frames as in live use). Output: JSON lines of 33 landmarks.
  * Angles at the exercise's three landmarks (2D, image plane) from the Unity landmarks are compared with the motion-capture skeleton
    projected into the same camera image, on exactly the frames where the Unity pipeline found a person.
  * The same frames are scored for MediaPipe (Python, full resolution, `*_2d.npy`) as a like-for-like baseline, and the Unity and
    MediaPipe angles are compared with each other.
  * 95% confidence intervals: bootstrap over recordings (the unit of independence), 2000 resamples.
Limits: motion capture is a reference, not ground truth; two exercises only (shoulder abduction, sit-to-stand, hip abduction), two cameras, 2D angles.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.exercises.library import get_exercise
from app.ml.angle_eval import error_metrics, paired_angles
from app.angle_calculation.angles import joint_angle
from app.ml.rehab26 import _landmarks


def load_unity(path: Path) -> dict[str, dict[int, np.ndarray]]:
    out: dict[str, dict[int, np.ndarray]] = defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        out[d["rec"]][d["frame"]] = None if d["lm"] is None else np.array(d["lm"], dtype=np.float64).reshape(33, 4)
    return out


def boot_ci(per_rec_abs: list[np.ndarray], n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    k = len(per_rec_abs)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, k, k)
        cat = np.concatenate([per_rec_abs[i] for i in idx])
        vals.append(cat.mean())
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def recordings(root: Path) -> list[tuple[str, str, int, str, str]]:
    """(dataset exercise id, video, camera, our exercise id, side): shoulder abduction (Ex1), sit-to-stand (Ex6) and hip abduction (Ex4).
    Hip abduction = the dataset's leg abduction; the side comes from the segmentation file and the more frontal camera is used."""
    import csv

    from app.ml.rehab24 import EXERCISES, choose_camera, needed_recordings

    out = [(exd, video, cam, EXERCISES[exd][0], EXERCISES[exd][1]) for (exd, video, cam) in needed_recordings(root)]
    seen = set()
    with (root / "Segmentation.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["exercise_id"] == "4" and r["mocap_erroneous"] != "1":
                cam = choose_camera(r["cam17_orientation"], 0)
                key = (r["video_id"], cam)
                if key not in seen:
                    seen.add(key)
                    out.append(("4", r["video_id"], cam, "hip_abduction", "RIGHT" if "right" in r["exercise_subtype"] else "LEFT"))
    return out


def evaluate(root: Path, unity_jsonl: Path) -> dict:
    from app.ml.rehab24 import to_mediapipe_layout

    unity = load_unity(unity_jsonl)
    pairs_u: list[tuple[float, float]] = []          # (unity angle, mocap angle)
    pairs_m: list[tuple[float, float]] = []          # (mediapipe angle, mocap angle) on the same frames
    pairs_um: list[tuple[float, float]] = []         # (unity angle, mediapipe angle)
    by_ex_u: dict = defaultdict(list); by_ex_m: dict = defaultdict(list)
    by_cam_u: dict = defaultdict(list); by_cam_m: dict = defaultdict(list)
    rec_abs_u: list[np.ndarray] = []; rec_abs_m: list[np.ndarray] = []
    sampled = found = 0
    foot_vis = []; z_range = []
    n_rec = 0
    for (exd, video, cam, ex_id, side) in recordings(root):
        key = f"Ex{exd}_{video}_c{cam}"
        if key not in unity:
            continue
        base = root / "mediapipe" / f"Ex{exd}" / f"{video}-c{cam}"
        if not base.with_name(base.name + "_meta.json").exists():
            continue
        meta = json.loads(base.with_name(base.name + "_meta.json").read_text(encoding="utf-8"))
        mp = np.load(base.with_name(base.name + "_2d.npy"), allow_pickle=False).astype(np.float64)
        mp[:, :, 0] *= meta["width"]; mp[:, :, 1] *= meta["height"]
        ref = to_mediapipe_layout(np.load(root / f"Ex{exd}" / f"{video}-c{cam}-30fps.npy", allow_pickle=False))
        ex = get_exercise(ex_id)
        names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
        # Unity landmarks to pixels of the original video (same aspect ratio as the downscaled frames)
        un = np.zeros_like(mp)
        frames = []
        for f, lm in unity[key].items():
            sampled += 1
            if lm is None or f >= len(mp) or f >= len(ref):
                continue
            found += 1
            a = lm.copy(); a[:, 0] *= meta["width"]; a[:, 1] *= meta["height"]
            un[f] = a; frames.append(f)
            foot_vis.append([lm[29, 3], lm[30, 3], lm[31, 3], lm[32, 3]]); z_range.append(float(np.ptp(lm[:, 2])))
        frames.sort()
        pu = paired_angles(un, ref, names, frames, 0)
        # same frames for MediaPipe: keep only frames where both Unity and MediaPipe angles exist
        ok = [f for f in frames if joint_angle(*_landmarks(un[f], names), min_conf=0.5) is not None
              and joint_angle(*_landmarks(mp[f], names), min_conf=0.5) is not None
              and joint_angle(*_landmarks(ref[f], names), min_conf=0.5) is not None]
        if len(ok) < 10:
            continue
        pu = paired_angles(un, ref, names, ok, 0); pm = paired_angles(mp, ref, names, ok, 0)
        pum = [(joint_angle(*_landmarks(un[f], names), min_conf=0.5), joint_angle(*_landmarks(mp[f], names), min_conf=0.5)) for f in ok]
        pairs_u += pu; pairs_m += pm; pairs_um += pum
        by_ex_u[ex_id] += pu; by_ex_m[ex_id] += pm; by_cam_u[cam] += pu; by_cam_m[cam] += pm
        rec_abs_u.append(np.array([abs(a - b) for a, b in pu])); rec_abs_m.append(np.array([abs(a - b) for a, b in pm]))
        n_rec += 1
    fv = np.array(foot_vis) if foot_vis else np.zeros((1, 4))
    ci_u, ci_m = boot_ci(rec_abs_u), boot_ci(rec_abs_m)
    diff = np.array([a - b for a, b in pairs_um])
    return {
        "recordings": n_rec, "frames_sampled": sampled, "frames_with_person_found": found,
        "detection_rate": found / sampled if sampled else None,
        "unity_vs_mocap": error_metrics(pairs_u), "unity_mae_ci95": ci_u,
        "mediapipe_vs_mocap_same_frames": error_metrics(pairs_m), "mediapipe_mae_ci95": ci_m,
        "unity_vs_mediapipe_mean_abs_diff_deg": float(np.abs(diff).mean()) if len(diff) else None,
        "by_exercise": {k: {"unity": error_metrics(by_ex_u[k]), "mediapipe": error_metrics(by_ex_m[k])} for k in by_ex_u},
        "by_camera": {f"cam{k}": {"unity": error_metrics(by_cam_u[k]), "mediapipe": error_metrics(by_cam_m[k])} for k in by_cam_u},
        "foot_points_mean_visibility": {"left_heel": float(fv[:, 0].mean()), "right_heel": float(fv[:, 1].mean()),
                                        "left_foot_index": float(fv[:, 2].mean()), "right_foot_index": float(fv[:, 3].mean())},
        "depth_z_range_median": float(np.median(z_range)) if z_range else None,
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]); jsonl = Path(sys.argv[2]); out = Path(sys.argv[3])
    res = evaluate(root, jsonl)
    out.write_text(json.dumps({
        "kind": "unity-pose",
        "title": "Unity on-device pose (BlazePose via Inference Engine) vs motion capture (REHAB24-6)",
        "caveat": "Reference = optical motion capture projected to the camera image (definitional differences count as error). 2D image-plane angles, three exercises, two cameras, frames every 3rd frame at 640 px wide, Unity CPU backend, single run.",
        "data": res}, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2)[:3000])
