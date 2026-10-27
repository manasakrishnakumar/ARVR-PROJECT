import json
import math

import numpy as np
import pytest

from app.ml import dataset as ds
from app.ml.own_recordings import FORMAT, RecordingError, import_recordings, load_recording, map_label, resample


def skeleton(n_reps=4, period=90, rest=30, peak=85.0):
    """SYNTHETIC right-arm abduction at 30 fps (normalised coordinates, all landmarks 'visible')."""
    n = rest + n_reps * (period + rest)
    a = np.zeros((n, 33, 4))
    a[:, :, 3] = 1.0
    a[:, 24, :2] = (0.5, 0.8)
    a[:, 12, :2] = (0.5, 0.5)
    a[:, 11, :2] = (0.6, 0.5)
    a[:, 23, :2] = (0.55, 0.8)
    th = np.full(n, 20.0)
    for r in range(n_reps):
        s = rest + r * (period + rest)
        th[s:s + period] = 20 + (peak - 20) * (1 - np.cos(2 * math.pi * np.arange(period) / period)) / 2
    for i, d in enumerate(th):
        a[i, 14, :2] = (0.5 + 0.2 * math.sin(math.radians(d)), 0.5 + 0.2 * math.cos(math.radians(d)))
    return a


def write(tmp, name, arr, fps=30, label="correct", error="", synthetic=False, **over):
    frames = [[round(i / fps, 4), arr[i].round(4).tolist()] for i in range(0, len(arr), 30 // fps if fps < 30 else 1)]
    rec = {"format": FORMAT, "created_utc": "2026-10-27T10:00:00Z", "participant_code": "P01", "exercise_id": "shoulder_abduction",
           "side": "right", "intended": {"label": label, "error": error}, "synthetic": synthetic,
           "camera": {"width": 640, "height": 480}, "model": "m", "frames": frames, **over}
    p = tmp / f"{name}.json"
    p.write_text(json.dumps(rec))
    return p


def test_label_mapping_from_intended_execution():
    assert map_label({"label": "correct", "error": ""}) == "acceptable"
    assert map_label({"label": "error", "error": "Insufficient arm raise"}) == "insufficient_range"
    assert map_label({"label": "error", "error": "Incomplete bend"}) == "incomplete_repetition"
    assert map_label({"label": "error", "error": "Moving too fast"}) == "too_fast"
    assert map_label({"label": "error", "error": "Trunk leaning"}) == "posture_deviation"
    assert map_label({"label": "error", "error": "other"}) == "incorrect_unspecified"


def test_import_finds_the_repetitions_and_labels_them(tmp_path):
    write(tmp_path, "take1", skeleton(4))
    write(tmp_path, "take2", skeleton(3), label="error", error="Trunk leaning")
    rows, stats = import_recordings(tmp_path)
    assert stats["recordings_imported"] == 2 and stats["repetitions"] == 7 and stats["problems"] == 0
    ds.validate_rows(rows)
    assert {r["label"] for r in rows if str(r["recording_id"]).startswith("take1")} == {"acceptable"}
    assert {r["label"] for r in rows if str(r["recording_id"]).startswith("take2")} == {"posture_deviation"}
    assert all(r["participant_id"] == "P01" and r["source"].startswith("own-recordings") and r["peak_progress"] > 0 for r in rows)


def test_lower_frame_rates_are_resampled_to_the_same_result(tmp_path):
    write(tmp_path, "slow", skeleton(4), fps=15)
    rows, stats = import_recordings(tmp_path)
    assert stats["repetitions"] == 4


def test_no_landmarks_are_invented_across_detection_gaps():
    arr = skeleton(4)
    rec = {"frames": [[round(i / 30, 4), arr[i].tolist()] for i in range(len(arr)) if not 60 <= i < 120]}  # 2 s without a person
    out = resample(rec)
    gap = out[int(2.05 * 30):int(3.9 * 30)]
    assert (gap[:, :, 3] == 0).all()  # visibility zero inside the gap
    assert (out[10:40, :, 3] > 0).all() and (out[150:200, :, 3] > 0).all()


def test_synthetic_recordings_are_kept_apart_by_default(tmp_path):
    write(tmp_path, "demo", skeleton(4), synthetic=True)
    rows, stats = import_recordings(tmp_path)
    assert rows == [] and stats["skipped_synthetic"] == 1
    rows, _ = import_recordings(tmp_path, include_synthetic=True)
    assert rows and all(r["source"] == "own-recordings-SYNTHETIC-demo" for r in rows)


def test_still_person_is_not_calibrated_into_fake_repetitions(tmp_path):
    flat = skeleton(0, rest=300)  # nobody moves
    write(tmp_path, "still", flat)
    rows, stats = import_recordings(tmp_path)
    assert rows == [] and stats["recordings_without_clear_movement"] == 1


@pytest.mark.parametrize("bad", [
    {"format": "something-else"}, {"exercise_id": "nope"}, {"side": "middle"}, {"intended": {"label": "maybe"}},
    {"camera": {"width": 0, "height": 480}}, {"frames": []}, {"participant_code": None, "frames": None},
])
def test_invalid_recordings_are_rejected_with_a_message_not_a_crash(tmp_path, bad):
    write(tmp_path, "bad", skeleton(2), **bad)
    with pytest.raises(RecordingError):
        load_recording(tmp_path / "bad.json")
    rows, stats = import_recordings(tmp_path)
    assert rows == [] and stats["rejected_files"] == 1 and stats["problem_messages"]


def test_malformed_frames_and_timestamps_are_rejected(tmp_path):
    arr = skeleton(2)
    p = write(tmp_path, "t", arr)
    rec = json.loads(p.read_text())
    rec["frames"][5][0] = rec["frames"][4][0]  # repeated timestamp
    p.write_text(json.dumps(rec))
    with pytest.raises(RecordingError, match="increasing"):
        load_recording(p)
    rec["frames"][5][0] = 99
    rec["frames"][6][1] = rec["frames"][6][1][:10]  # not 33 landmarks
    p.write_text(json.dumps(rec))
    with pytest.raises(RecordingError, match="33"):
        load_recording(p)
    (tmp_path / "junk.json").write_text("{not json")
    with pytest.raises(RecordingError, match="not readable"):
        load_recording(tmp_path / "junk.json")
