"""Import recordings made with the app's "Record data" page (arvr-landmarks-v1 JSON: landmark numbers only, no video).

Each recording is one take of one exercise with a known intended execution (correct, or a deliberate error). Repetitions are
found by the auto-calibrated counter (validated in the counting evaluation) and every repetition inherits the take's label.
That is weaker than per-repetition labels from an annotator: take-level labels assume the person really did every repetition
the way they intended. Raw recordings are personal data: keep them out of git (datasets/own/ is git-ignored).
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.exercises.library import get_exercise
from app.ml.count_eval import angle_series, auto_range, detect
from app.ml.dataset import Row
from app.ml.rehab26 import FPS, build_rep_row

FORMAT = "arvr-landmarks-v1"
SOURCE = "own-recordings (local, consented)"
SOURCE_SYNTHETIC = "own-recordings-SYNTHETIC-demo"
MAX_GAP_S = 0.25  # across a longer gap in detections no landmarks are invented
MIN_FRAMES = 30


class RecordingError(ValueError):
    pass


def load_recording(path: Path) -> dict:
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RecordingError(f"{path.name}: not readable JSON ({e})") from e
    if not isinstance(rec, dict) or rec.get("format") != FORMAT:
        raise RecordingError(f"{path.name}: not an {FORMAT} recording")
    for k in ("participant_code", "exercise_id", "side", "intended", "camera", "frames"):
        if k not in rec:
            raise RecordingError(f"{path.name}: missing '{k}'")
    if rec["side"] not in ("left", "right"):
        raise RecordingError(f"{path.name}: side must be left or right")
    if get_exercise(rec["exercise_id"]) is None:
        raise RecordingError(f"{path.name}: unknown exercise '{rec['exercise_id']}'")
    intended = rec["intended"]
    if not isinstance(intended, dict) or intended.get("label") not in ("correct", "error"):
        raise RecordingError(f"{path.name}: intended.label must be 'correct' or 'error'")
    frames = rec["frames"]
    if not isinstance(frames, list) or len(frames) < MIN_FRAMES:
        raise RecordingError(f"{path.name}: needs at least {MIN_FRAMES} frames")
    last_t = -1.0
    for f in frames:
        if not (isinstance(f, list) and len(f) == 2 and isinstance(f[1], list) and len(f[1]) == 33 and all(len(p) == 4 for p in f[1])):
            raise RecordingError(f"{path.name}: every frame must be [time, 33 x [x, y, z, visibility]]")
        if not isinstance(f[0], (int, float)) or f[0] <= last_t:
            raise RecordingError(f"{path.name}: timestamps must be strictly increasing numbers")
        last_t = f[0]
    cam = rec["camera"]
    if not (isinstance(cam, dict) and cam.get("width", 0) > 0 and cam.get("height", 0) > 0):
        raise RecordingError(f"{path.name}: camera width/height missing")
    return rec


def resample(rec: dict, fps: float = FPS) -> np.ndarray:
    """(T, 33, 4) at a constant frame rate. Coordinates are interpolated linearly; visibility is set to 0 inside detection gaps."""
    t = np.array([f[0] for f in rec["frames"]], dtype=float)
    lm = np.array([f[1] for f in rec["frames"]], dtype=float)  # (N, 33, 4)
    grid = np.arange(t[0], t[-1], 1.0 / fps)
    out = np.empty((len(grid), 33, 4))
    for j in range(33):
        for c in range(3):
            out[:, j, c] = np.interp(grid, t, lm[:, j, c])
        out[:, j, 3] = np.interp(grid, t, lm[:, j, 3])
    # no invented landmarks across gaps (frames are only recorded while a person is detected)
    idx = np.searchsorted(t, grid, side="right") - 1
    nxt = np.clip(idx + 1, 0, len(t) - 1)
    in_gap = (t[nxt] - t[np.clip(idx, 0, len(t) - 1)]) > MAX_GAP_S
    out[in_gap, :, 3] = 0.0
    return out


def map_label(intended: dict) -> str:
    """Take-level label from the intended execution: error text -> the closest label of the project's label set."""
    if intended["label"] == "correct":
        return "acceptable"
    e = str(intended.get("error", "")).lower()
    if any(w in e for w in ("insufficient", "shallow", "low ", "too little", "not high", "short")):
        return "insufficient_range"
    if "incomplete" in e:
        return "incomplete_repetition"
    if "fast" in e or "quick" in e:
        return "too_fast"
    if "uncontrolled" in e or "jerk" in e:
        return "uncontrolled"
    if e in ("", "other"):
        return "incorrect_unspecified"
    return "posture_deviation"


def import_recordings(directory: Path, include_synthetic: bool = False, min_conf: float = 0.5) -> tuple[list[Row], dict]:
    rows: list[Row] = []
    stats: dict[str, int] = defaultdict(int)
    problems: list[str] = []
    for path in sorted(directory.glob("*.json")):
        try:
            rec = load_recording(path)
        except RecordingError as e:
            stats["rejected_files"] += 1
            problems.append(str(e))
            continue
        if rec.get("synthetic") and not include_synthetic:
            stats["skipped_synthetic"] += 1
            continue
        ex = get_exercise(rec["exercise_id"])
        assert ex is not None
        side = rec["side"].upper()
        arr = resample(rec)
        arr[:, :, 0] *= rec["camera"]["width"] / rec["camera"]["height"]  # equalise the x and y scales
        names = [n.replace("LEFT_", f"{side}_") for n in ex.landmarks]
        angles = angle_series(arr, names, min_conf)
        rng = auto_range(angles, ex)
        if rng is None:
            stats["recordings_without_clear_movement"] += 1
            continue
        found = detect(angles, rng[0], rng[1], 0.6, 0.1 * abs(rng[1] - rng[0]))
        label = map_label(rec["intended"])
        for i, (first, last, _) in enumerate(found, 1):
            row = build_rep_row(arr, None, ex, side, first, last, i, min_conf, {
                "participant_id": str(rec["participant_code"]), "recording_id": f"{path.stem}-r{i}", "exercise_id": ex.id,
                "label": label, "source": SOURCE_SYNTHETIC if rec.get("synthetic") else SOURCE, "camera": 0,
                "orientation_deg": "", "error_code": str(rec["intended"].get("error", ""))})
            if row is None:
                stats["skipped_too_few_valid_frames"] += 1
                continue
            rows.append(row)
            stats["repetitions"] += 1
        stats["recordings_imported"] += 1
    stats["problems"] = len(problems)  # type: ignore[assignment]
    return rows, {**stats, "problem_messages": problems}  # type: ignore[dict-item]
