import csv
import math

import numpy as np
import pytest

from app.ml import dataset as ds
from app.ml.rehab24 import MOCAP_TO_MP, choose_camera, import_rehab24, to_mediapipe_layout

HEADER = ["video_id", "repetition_number", "exercise_id", "person_id", "first_frame", "last_frame", "cam17_orientation",
          "mocap_erroneous", "exercise_subtype", "lights_on", "extra_person_in_cam17", "extra_person_in_cam18", "correctness"]


def _mocap(peaks):
    """SYNTHETIC 26-joint pixel skeleton; right arm abducts to each peak angle (y grows downward)."""
    a = np.zeros((60 * len(peaks), 26, 2))
    base = {7: (600, 400), 12: (400, 400), 8: (620, 650), 9: (620, 850), 14: (400, 850), 16: (560, 700),
            21: (440, 700), 17: (560, 950), 22: (440, 950), 18: (560, 1150), 23: (440, 1150),
            20: (600, 1180), 25: (400, 1180)}
    for j, (x, y) in base.items():
        a[:, j] = (x, y)
    for i, peak in enumerate(peaks):
        for k in range(60):
            th = math.radians(20 + (peak - 20) * math.sin(math.pi * k / 59))
            a[i * 60 + k, 13] = (400 + 300 * math.sin(th), 400 + 300 * math.cos(th))  # right forearm joint (elbow)
    return a


@pytest.fixture
def root(tmp_path):
    (tmp_path / "Ex1").mkdir()
    rows = []
    for p in (1, 2, 3):
        np.save(tmp_path / "Ex1" / f"PM_{p:03d}-c17-30fps.npy", _mocap([90, 40]))
        rows += [[f"PM_{p:03d}", 1, 1, p, 0, 59, "front", 0, "right arm", 1, 0, 0, 1],
                 [f"PM_{p:03d}", 2, 1, p, 60, 119, "front", 0, "right arm", 1, 0, 0, 0]]
    rows.append(["PM_001", 3, 1, 1, 0, 59, "front", 1, "right arm", 1, 0, 0, 1])  # mocap flagged erroneous
    rows.append(["PM_009", 1, 2, 9, 0, 59, "front", 0, "", 1, 0, 0, 1])  # exercise we do not support
    rows.append(["PM_077", 1, 1, 7, 0, 59, "front", 0, "right arm", 1, 0, 0, 1])  # file missing
    with (tmp_path / "Segmentation.csv").open("w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(HEADER)
        w.writerows(rows)
    return tmp_path


def test_layout_mapping_marks_missing_landmarks_invisible():
    out = to_mediapipe_layout(np.ones((4, 26, 2)))
    assert out.shape == (4, 33, 4)
    for mp in MOCAP_TO_MP:
        assert out[0, mp, 3] == 1.0
    assert out[0, 7, 3] == 0.0 and out[0, 29, 3] == 0.0  # ears and heels do not exist in the mocap skeleton


def test_camera_choice_uses_orientation():
    assert choose_camera("front", 0) == 17 and choose_camera("profile", 0) == 18  # cam18 is orthogonal to cam17
    assert choose_camera("front", 90) == 18 and choose_camera("profile", 90) == 17
    assert choose_camera("half-profile", 0) in (17, 18)


def test_import_labels_and_skips(root):
    rows, stats = import_rehab24(root)
    assert stats == {"skipped_mocap_erroneous": 1, "skipped_exercise_not_supported": 1, "skipped_missing_file": 1,
                     "imported": 6}
    ds.validate_rows(rows)
    good = next(r for r in rows if r["recording_id"] == "PM_001-r1")
    bad = next(r for r in rows if r["recording_id"] == "PM_001-r2")
    assert good["label"] == "acceptable" and bad["label"] == "incorrect_unspecified"
    assert good["peak_progress"] > 0.85 and bad["peak_progress"] < 0.5  # angles are smoothed, so the peak is trimmed
    assert good["source"].startswith("rehab24-6") and good["participant_id"] == "P1"
