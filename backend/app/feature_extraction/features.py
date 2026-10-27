"""Per-repetition movement features (all from a single camera's 2D joint angle)."""
from app.repetition_detection.counter import Repetition

_VEL_NOISE_DEG_S = 5.0


def rep_features(rep: Repetition) -> dict[str, float]:
    ts, an = rep.times, rep.angles
    vels = [(an[i + 1] - an[i]) / (ts[i + 1] - ts[i]) for i in range(len(ts) - 1) if ts[i + 1] > ts[i]]
    signs = [1 if v > 0 else -1 for v in vels if abs(v) >= _VEL_NOISE_DEG_S]
    flips = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])
    return {
        "rom_deg": (max(an) - min(an)) if an else 0.0,
        "duration_s": rep.duration_s,
        "peak_velocity_deg_s": max((abs(v) for v in vels), default=0.0),
        "mean_speed_deg_s": (sum(abs(v) for v in vels) / len(vels)) if vels else 0.0,
        "extra_reversals": float(max(0, flips - 1)),  # a clean rep reverses direction once
        "peak_progress": rep.peak_progress,
        "reliability": 1.0 - rep.n_missing / rep.n_frames if rep.n_frames else 0.0,
    }
