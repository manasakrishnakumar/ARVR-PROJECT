"""Exercise-agnostic feature vector for the ML classifier (angles normalised by the exercise range)."""
from app.exercises.library import Exercise

FEATURE_NAMES = ["peak_progress", "rom_fraction", "duration_s", "peak_velocity_norm", "mean_speed_norm",
                 "extra_reversals", "reliability"]


def ml_features(raw: dict, ex: Exercise) -> list[float]:
    span = abs(ex.target_angle_deg - ex.start_angle_deg)
    return [
        float(raw["peak_progress"]), float(raw["rom_deg"]) / span, float(raw["duration_s"]),
        float(raw["peak_velocity_deg_s"]) / span, float(raw["mean_speed_deg_s"]) / span,
        float(raw["extra_reversals"]), float(raw["reliability"]),
    ]
