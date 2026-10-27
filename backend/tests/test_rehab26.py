import csv
import math

import numpy as np
import pytest

from app.ml import dataset as ds
from app.ml.lopo import run_lopo
from app.ml.rehab26 import choose_camera, import_rehab26, map_label

HEADER = ["video_id", "exercise_id", "exercise_subtype", "person", "repetition_number", "first_frame", "last_frame",
          "person_orientation", "correctness_score", "error_description", "additional_errors"]


def _skeleton(peaks: list[float]) -> np.ndarray:
    """SYNTHETIC right-arm abduction: shoulder angle (hip-shoulder-elbow) rises from 20 deg to each peak."""
    a = np.zeros((60 * len(peaks), 33, 4))
    a[:, :, 3] = 1.0
    a[:, 24, :2] = (0.5, 0.8)  # right hip
    a[:, 12, :2] = (0.5, 0.5)  # right shoulder
    for i, peak in enumerate(peaks):
        for k in range(60):
            th = math.radians(20 + (peak - 20) * math.sin(math.pi * k / 59))
            a[i * 60 + k, 14, :2] = (0.5 + 0.2 * math.sin(th), 0.5 + 0.2 * math.cos(th))  # right elbow
    return a


@pytest.fixture
def root(tmp_path):
    (tmp_path / "mediapipe" / "ex1").mkdir(parents=True)
    rows = []
    for p in ("A", "B", "C"):
        np.save(tmp_path / "mediapipe" / "ex1" / f"ex1_{p}_cam1_2d.npy", _skeleton([90, 40, 90]))
        for i, (score, err) in enumerate([("1", ""), ("5", "ERR_LOW_ABDUCTION"), ("5", "ERR_ARM_FORWARD")]):
            rows.append([f"ex1_{p}", "1", "right", p, i + 1, i * 60, i * 60 + 59, 0, score, err, ""])
    rows.append(["ex1_MISSING", "1", "right", "D", 1, 0, 59, 0, "1", "", ""])  # no skeleton file
    rows.append(["ex7_A", "7", "right", "A", 1, 0, 59, 0, "1", "", ""])  # exercise we do not support
    with (tmp_path / "Segmentation.csv").open("w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(HEADER)
        w.writerows(rows)
    return tmp_path


def test_label_mapping_and_camera_choice():
    assert map_label("1", "") == "acceptable"
    assert map_label("5", "ERR_LOW_ABDUCTION") == "insufficient_range"
    assert map_label("5", "ERR_SHALLOW_SQUAT") == "insufficient_range"
    assert map_label("5", "ERR_ELEVATED_SHOULDER") == "posture_deviation"
    assert choose_camera(0, 0) == 1 and choose_camera(90, 0) == 3 and choose_camera(45, 0) == 2
    assert choose_camera(0, 90) == 3 and choose_camera(90, 90) == 1


def test_import_counts_labels_and_skips(root):
    rows, stats = import_rehab26(root)
    assert stats == {"skipped_exercise_not_supported": 1, "skipped_missing_file": 1, "imported": 9,
                     "missing_3d_file": 9}  # fixture has no 3D skeletons: 3D features fall back to zeros
    ds.validate_rows(rows)
    by = {(r["participant_id"], r["recording_id"].split("-r")[1]): r for r in rows}
    assert by[("A", "1")]["label"] == "acceptable" and by[("A", "2")]["label"] == "insufficient_range"
    assert by[("A", "3")]["label"] == "posture_deviation"
    assert by[("A", "1")]["peak_progress"] > 0.9 and by[("A", "2")]["peak_progress"] < 0.5
    assert by[("A", "1")]["reliability"] == 1.0 and by[("A", "1")]["source"].startswith("rehab26")


def test_low_visibility_frames_counted_as_missing(root):
    arr = np.load(root / "mediapipe" / "ex1" / "ex1_A_cam1_2d.npy")
    arr[10:20, 14, 3] = 0.1  # elbow not visible for 10 frames of rep 1
    np.save(root / "mediapipe" / "ex1" / "ex1_A_cam1_2d.npy", arr)
    rows, _ = import_rehab26(root)
    rep1 = next(r for r in rows if r["recording_id"] == "ex1_A-r1")
    assert rep1["reliability"] == pytest.approx(1 - 10 / 60)


def test_csv_roundtrip_keeps_extra_columns_and_lopo_runs(root, tmp_path):
    rows, _ = import_rehab26(root)
    out = tmp_path / "reps.csv"
    ds.write_csv(rows, out)
    back = ds.read_csv(out)
    assert len(back) == 9 and back[0]["camera"] == "1"
    ev = run_lopo(back, n_boot=5)
    assert ev["participants"] == ["A", "B", "C"] and ev["n"] == 9
    assert set(ev["methods"]) == {"majority_class", "rule_based", "rule_range_tuned", "rf_base", "rf_base_tuned",
                                  "rf_posture", "rf_posture_tuned"}
    assert "binary_correct_vs_incorrect" in ev["methods"]["rf_posture_tuned"]
    # tuning is chosen per fold from training participants; each fold records its held-out person
    assert {t["held_out"] for t in ev["tuning"]["rf_base_tuned"]} == {"A", "B", "C"}


def test_lopo_needs_three_participants(root):
    rows, _ = import_rehab26(root)
    with pytest.raises(ValueError):
        run_lopo([r for r in rows if r["participant_id"] in ("A", "B")], n_boot=5)
