"""SYNTHETIC angle sequences for tests and demos. Not real human movement data."""
import math
import random


def make_sequence(start: float, target: float, n_reps: int, period_s: float = 3.0, fps: int = 30,
                  depth: float = 1.0, noise_deg: float = 0.0, dropout: float = 0.0, rest_s: float = 1.0,
                  seed: int = 0) -> list[tuple[float, float | None]]:
    """Smooth rest -> target -> rest cycles. depth=1 reaches the target; depth<1 falls short."""
    rng = random.Random(seed)
    out: list[tuple[float, float | None]] = []
    t = 0.0
    dt = 1.0 / fps

    def emit(angle: float) -> None:
        nonlocal t
        a: float | None = angle + rng.gauss(0, noise_deg) if noise_deg else angle
        if dropout and rng.random() < dropout:
            a = None
        out.append((t, a))
        t += dt

    for _ in range(int(rest_s * fps)):
        emit(start)
    for _ in range(n_reps):
        for k in range(int(period_s * fps)):
            p = depth * (1 - math.cos(2 * math.pi * k / (period_s * fps))) / 2
            emit(start + p * (target - start))
        for _ in range(int(rest_s * fps)):
            emit(start)
    return out
