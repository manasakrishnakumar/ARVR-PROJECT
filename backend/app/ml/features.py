"""Exercise-agnostic feature vectors for the ML classifier (angles normalised by the exercise range)."""
from app.exercises.library import Exercise

FEATURE_NAMES = ["peak_progress", "rom_fraction", "duration_s", "peak_velocity_norm", "mean_speed_norm",
                 "extra_reversals", "reliability"]
POSTURE_FEATURES = ["torso_tilt_dev_max", "torso_tilt_dev_mean", "shoulder_asym_dev_max", "head_tilt_dev_max",
                    "elbow_bend_min_deg", "elbow_bend_min_3d_deg", "lr_angle_asym_mean_deg", "rom3d_deg",
                    "peak3d_minus_2d_progress", "knee_valgus_dev_max", "heel_lift_dev_max", "knee_over_toe_dev_max",
                    "lower_body_exercise", "posture_reliability"]
FEATURE_NAMES_POSTURE = FEATURE_NAMES + POSTURE_FEATURES


def ml_features(raw: dict, ex: Exercise, posture: bool = False) -> list[float]:
    span = abs(ex.target_angle_deg - ex.start_angle_deg)
    base = [
        float(raw["peak_progress"]), float(raw["rom_deg"]) / span, float(raw["duration_s"]),
        float(raw["peak_velocity_deg_s"]) / span, float(raw["mean_speed_deg_s"]) / span,
        float(raw["extra_reversals"]), float(raw["reliability"]),
    ]
    return base + [float(raw[k]) for k in POSTURE_FEATURES] if posture else base
