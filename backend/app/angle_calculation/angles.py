"""Joint-angle maths.

Angles are computed in the IMAGE PLANE (2D) or from whatever coordinates are
supplied. Monocular webcam values are NOT clinically accurate 3D anatomical angles.
"""
import math
from dataclasses import dataclass

MIN_CONFIDENCE = 0.5
_EPS = 1e-9


@dataclass(frozen=True)
class Landmark:
    x: float
    y: float
    z: float = 0.0
    confidence: float = 1.0


def _valid(p: Landmark | None, min_conf: float) -> bool:
    if p is None:
        return False
    vals = (p.x, p.y, p.z, p.confidence)
    return all(math.isfinite(v) for v in vals) and p.confidence >= min_conf


def joint_angle(a: Landmark | None, b: Landmark | None, c: Landmark | None,
                min_conf: float = MIN_CONFIDENCE, use_z: bool = False) -> float | None:
    """Angle in degrees at vertex b between rays b->a and b->c.

    Returns None if any landmark is missing, non-finite, low-confidence, or a
    segment has zero length (angle undefined).
    """
    if not all(_valid(p, min_conf) for p in (a, b, c)):
        return None
    dim = 3 if use_z else 2
    ba = [getattr(a, k) - getattr(b, k) for k in "xyz"[:dim]]
    bc = [getattr(c, k) - getattr(b, k) for k in "xyz"[:dim]]
    na = math.sqrt(sum(v * v for v in ba))
    nc = math.sqrt(sum(v * v for v in bc))
    if na < _EPS or nc < _EPS:
        return None
    cos = sum(p * q for p, q in zip(ba, bc)) / (na * nc)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


class AngleSmoother:
    """Exponential moving average that skips missing values and rejects spikes."""

    def __init__(self, alpha: float = 0.4, max_jump_deg: float = 60.0):
        self.alpha, self.max_jump, self.value = alpha, max_jump_deg, None

    def update(self, angle: float | None) -> float | None:
        if angle is None:
            return self.value
        if self.value is None:
            self.value = angle
        elif abs(angle - self.value) <= self.max_jump:
            self.value = self.alpha * angle + (1 - self.alpha) * self.value
        return self.value
