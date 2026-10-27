import csv
import json
import math

import numpy as np
import pytest

from app.ml import dataset as ds
from app.ml.rehab24 import import_rehab24_video, needed_recordings, video_entry_name
from app.ml.external import external_validation
from app.ml.rehab24 import SOURCE_VIDEO

HEADER = ["video_id", "repetition_number", "exercise_id", "person_id", "first_frame", "last_frame", "cam17_orientation",
          "mocap_erroneous", "exercise_subtype", "lights_on", "extra_person_in_cam17", "extra_person_in_cam18", "correctness"]


def _mp_skeleton(peaks):
    """SYNTHETIC MediaPipe-layout array (normalised coords, 3D in metres); right arm abducts to each peak."""
    a = np.zeros((60 * len(peaks), 33, 4), np.float32)
    a[:, :, 3] = 1.0
    a[:, 24, :2] = (0.5, 0.8)
    a[:, 12, :2] = (0.5, 0.5)
    a[:, 11, :2] = (0.6, 0.5)
    a[:, 23, :2] = (0.55, 0.8)
    for i, peak in enumerate(peaks):
        for k in range(60):
            th = math.radians(20 + (peak - 20) * math.sin(math.pi * k / 59))
            a[i * 60 + k, 14, :2] = (0.5 + 0.2 * math.sin(th), 0.5 + 0.2 * math.cos(th))
    return a


@pytest.fixture
def root(tmp_path):
    (tmp_path / "mediapipe" / "Ex1").mkdir(parents=True)
    rows = []
    for p in (1, 2, 3):
        base = tmp_path / "mediapipe" / "Ex1" / f"PM_{p:03d}-c17"
        a = _mp_skeleton([90, 40])
        np.save(base.with_name(base.name + "_2d.npy"), a)
        np.save(base.with_name(base.name + "_3d.npy"), a)
        base.with_name(base.name + "_meta.json").write_text(json.dumps({"width": 1920, "height": 1080, "fps": 30}))
        rows += [[f"PM_{p:03d}", 1, 1, p, 0, 59, "front", 0, "right arm", 1, 0, 0, 1],
                 [f"PM_{p:03d}", 2, 1, p, 60, 119, "front", 0, "right arm", 1, 0, 0, 0]]
    rows.append(["PM_050", 1, 1, 5, 0, 59, "front", 0, "right arm", 1, 0, 0, 1])  # never extracted
    with (tmp_path / "Segmentation.csv").open("w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(HEADER)
        w.writerows(rows)
    return tmp_path


def test_needed_recordings_and_entry_names(root):
    need = needed_recordings(root)
    assert ("1", "PM_001", 17) in need and need[("1", "PM_001", 17)] == [(0, 59), (60, 119)]
    entries = {"Ex1/PM_001-Camera17-30fps.mp4": 1, "Ex1/PM_001-Camera18-30fps-transposed.mp4": 2}
    assert video_entry_name(entries, "1", "PM_001", 17) == "Ex1/PM_001-Camera17-30fps.mp4"
    assert video_entry_name(entries, "1", "PM_001", 18) == "Ex1/PM_001-Camera18-30fps-transposed.mp4"
    assert video_entry_name(entries, "1", "PM_999", 17) is None


def test_video_import_uses_aspect_3d_and_marks_source(root):
    rows, stats = import_rehab24_video(root)
    assert stats == {"imported": 6, "skipped_not_extracted": 1}
    ds.validate_rows(rows)
    r = next(r for r in rows if r["recording_id"] == "PM_001-r1")
    assert r["source"] == SOURCE_VIDEO and r["label"] == "acceptable" and r["participant_id"] == "P1"
    assert r["rom3d_deg"] > 0  # 3D features are available for the video-based import (unlike mocap joints)
    assert r["peak_progress"] > 0.3


def test_full_feature_set_option_in_external_validation(root):
    rows, _ = import_rehab24_video(root)
    train = [{**r, "participant_id": "T" + str(r["participant_id"])} for r in rows]
    ev = external_validation(train, rows, n_boot=5, full_features=True)
    assert any("angle_plus_posture_full" in k for k in ev["methods"])
    assert "rf_angle_plus_posture_full" in ev["in_domain_reference_loo_participant"]
    assert not any("angle_plus_posture_full" in k for k in external_validation(train, rows, n_boot=5)["methods"])
