"""Per-user range calibration.

The exercise definitions hold ILLUSTRATIVE start/target angles, which rarely match a particular body or camera view. Calibration
measures the range the user actually demonstrates in the first seconds of a session (10th to 90th percentile of the smoothed
angle) and uses it for counting. It describes what the user did, not what they should do: it is not a clinical target.
"""
import numpy as np

from app.exercises.library import Exercise

MIN_SECONDS = 5.0  # observed time before calibration may complete
MIN_VALID = 30  # valid (non-missing) smoothed samples needed
MIN_RANGE_DEG = 15.0  # smaller movement than this cannot be calibrated (the person is not moving)


def estimate_range(values: list[float], ex: Exercise) -> tuple[float, float] | None:
    """(start, target) from observed angles, in the exercise's movement direction; None if there is not enough movement."""
    if len(values) < MIN_VALID:
        return None
    lo, hi = float(np.percentile(values, 10)), float(np.percentile(values, 90))
    if hi - lo < MIN_RANGE_DEG:
        return None
    return (lo, hi) if ex.target_angle_deg > ex.start_angle_deg else (hi, lo)
