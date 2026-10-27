import numpy as np
import pytest

from app.ml.video_pose import extract_ranges, merge_ranges

cv2 = pytest.importorskip("cv2")


def test_merge_ranges_pads_and_merges():
    assert merge_ranges([(10, 20), (25, 30)], pad=2, max_gap=10) == [(8, 30)]  # close ranges join
    assert merge_ranges([(10, 20), (300, 320)], pad=0, max_gap=10) == [(10, 20), (300, 320)]
    assert merge_ranges([(2, 5)], pad=5) == [(0, 5)]  # never negative
    assert merge_ranges([]) == []


class FakeDetector:
    """Records which frames it is asked about; encodes the frame's brightness into the landmark x."""
    created = 0
    seen: list[int] = []

    def __init__(self):
        FakeDetector.created += 1

    def detect(self, frame_rgb, ts):
        FakeDetector.seen.append(ts)
        lm = np.zeros((33, 4), np.float32)
        lm[:, 0] = frame_rgb.mean() / 255.0
        lm[:, 3] = 1.0
        return lm, lm.copy()

    def close(self):
        pass


@pytest.fixture
def video(tmp_path):
    """SYNTHETIC 40-frame 20 fps clip; frame i has grey level 5*i (lossy codec, so compared loosely)."""
    path = tmp_path / "clip.avi"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 20.0, (64, 48))
    for i in range(40):
        w.write(np.full((48, 64, 3), 5 * i, np.uint8))
    w.release()
    return path


def test_only_requested_frames_are_processed_with_exact_indices(video):
    FakeDetector.created, FakeDetector.seen = 0, []
    a2d, a3d, meta = extract_ranges(video, [(5, 9), (30, 34)], FakeDetector, pad=5, max_gap=5)
    assert a2d.shape == (40, 33, 4) and meta["width"] == 64 and meta["height"] == 48 and meta["frames"] == 40
    assert FakeDetector.created == 2  # separate ranges get fresh tracking state
    processed = np.where(a2d[:, 0, 3] > 0)[0]
    assert processed.min() == 0 and processed.max() == 34  # padded start, requested end
    assert not a2d[10:25].any() and not a2d[36:].any()  # nothing outside the ranges
    # frame content maps to the right index (grey ~ 5*i)
    assert a2d[32, 0, 0] == pytest.approx(5 * 32 / 255.0, abs=0.03)
    assert meta["processed"] == meta["detected"] == len(processed)


def test_missing_video_and_ranges_beyond_end(video, tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_ranges(tmp_path / "nope.avi", [(0, 5)], FakeDetector)
    a2d, _, meta = extract_ranges(video, [(35, 500), (900, 950)], FakeDetector)
    assert meta["frames"] == 40 and a2d[39, 0, 3] == 1.0 and a2d.shape[0] == 40
