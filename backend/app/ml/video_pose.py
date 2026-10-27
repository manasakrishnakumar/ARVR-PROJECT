"""Run a pose estimator over selected frame ranges of a video (optional dependencies: opencv-python, mediapipe).

Only frames inside the labelled repetition ranges are processed. Results are (frames, 33, 4) arrays holding x, y,
z, visibility per landmark (same layout as the REHAB26 MediaPipe files); frames that were not processed, or where
no person was found, are all-zero (visibility 0). No video frames are stored.
"""
from pathlib import Path
from typing import Callable, Protocol

import numpy as np


class Detector(Protocol):
    def detect(self, frame_rgb: np.ndarray, timestamp_ms: int) -> tuple[np.ndarray | None, np.ndarray | None]:
        """-> (image landmarks (33,4), world landmarks (33,4)) or (None, None) when no person is found"""

    def close(self) -> None: ...


def merge_ranges(ranges: list[tuple[int, int]], pad: int = 5, max_gap: int = 90) -> list[tuple[int, int]]:
    """Pad each (first, last) range and merge ranges that overlap or are closer than max_gap frames."""
    out: list[list[int]] = []
    for a, b in sorted((max(0, a - pad), b) for a, b in ranges):
        if out and a - out[-1][1] <= max_gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def extract_ranges(video: Path, ranges: list[tuple[int, int]], make_detector: Callable[[], Detector],
                   pad: int = 5, max_gap: int = 90) -> tuple[np.ndarray, np.ndarray, dict]:
    import cv2  # optional dependency

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    a2d, a3d = np.zeros((total, 33, 4), np.float32), np.zeros((total, 33, 4), np.float32)
    merged = merge_ranges([(a, min(b, total - 1)) for a, b in ranges if a < total], pad, max_gap)
    detected = processed = 0
    detector: Detector | None = None
    idx, k = 0, 0  # frame index, index of the current merged range
    try:
        while k < len(merged):
            start, end = merged[k]
            if idx > end:
                k += 1
                if detector is not None:
                    detector.close()
                    detector = None  # fresh tracking state for the next, separate range
                continue
            if idx < start:
                if not cap.grab():
                    break
                idx += 1
                continue
            ok, frame = cap.read()
            if not ok:
                break
            if detector is None:
                detector = make_detector()
            lm2d, lm3d = detector.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), int(round(idx * 1000 / fps)))
            processed += 1
            if lm2d is not None:
                a2d[idx], a3d[idx] = lm2d, lm3d if lm3d is not None else 0
                detected += 1
            idx += 1
    finally:
        if detector is not None:
            detector.close()
        cap.release()
    return a2d, a3d, {"width": width, "height": height, "fps": fps, "frames": total, "processed": processed,
                      "detected": detected}


class MediaPipeDetector:
    """Wraps the MediaPipe Pose Landmarker (tasks API) in VIDEO mode."""

    def __init__(self, model_path: Path):
        from mediapipe.tasks.python import BaseOptions, vision

        self._vision = vision
        self._lm = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)), running_mode=vision.RunningMode.VIDEO,
            num_poses=1))

    def detect(self, frame_rgb: np.ndarray, timestamp_ms: int):
        import mediapipe as mp

        res = self._lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame_rgb)),
                                        timestamp_ms)
        if not res.pose_landmarks:
            return None, None
        img = np.array([[l.x, l.y, l.z, l.visibility or 0.0] for l in res.pose_landmarks[0]], np.float32)
        world = np.array([[l.x, l.y, l.z, l.visibility or 0.0] for l in res.pose_world_landmarks[0]], np.float32)
        return img, world

    def close(self) -> None:
        self._lm.close()
