"""SYNTHETIC repetition dataset. Labels come from the generating condition, not from human annotation.

Useful for exercising the pipeline end to end. It says NOTHING about accuracy on real human movement,
and because the conditions mirror the rule thresholds, it cannot show which method is better in practice.
"""
import random

from app.angle_calculation.angles import AngleSmoother
from app.exercises.library import load_exercises
from app.feature_extraction.features import rep_features
from app.ml.dataset import Row
from app.repetition_detection.counter import RepConfig, RepetitionCounter
from app.synthetic.sequences import make_sequence

# label -> sampler of make_sequence keyword arguments
CONDITIONS = {
    "acceptable": lambda r: dict(depth=r.uniform(0.78, 1.0), period_s=r.uniform(2.0, 4.0)),
    "insufficient_range": lambda r: dict(depth=r.uniform(0.42, 0.62), period_s=r.uniform(2.0, 4.0)),
    "incomplete_repetition": lambda r: dict(depth=r.uniform(0.2, 0.36), period_s=r.uniform(2.0, 4.0)),
    "too_fast": lambda r: dict(depth=r.uniform(0.85, 1.0), period_s=r.uniform(0.7, 1.3)),
    "uncontrolled": lambda r: dict(depth=r.uniform(0.85, 1.0), period_s=r.uniform(2.5, 4.0),
                                   tremor_deg=r.uniform(7, 14), tremor_hz=r.uniform(2.0, 3.0)),
    "insufficient_data": lambda r: dict(depth=r.uniform(0.85, 1.0), period_s=r.uniform(2.5, 4.0),
                                        dropout=r.uniform(0.4, 0.6)),
}


SYNTHETIC_EXERCISES = ("elbow_flexion", "knee_flexion", "shoulder_abduction", "shoulder_extension", "shoulder_flexion", "sit_to_stand")


def generate_dataset(n_participants: int = 20, reps_per_condition: int = 4, seed: int = 0) -> list[Row]:
    rng = random.Random(seed)
    library = load_exercises()
    exercises = [library[i] for i in SYNTHETIC_EXERCISES]  # fixed set: adding exercises to the library must not change this dataset
    rows: list[Row] = []
    for p in range(n_participants):
        pid = f"S{p:03d}"
        noise = rng.uniform(0.5, 2.5)  # participant-specific tracking noise
        for label, sample in CONDITIONS.items():
            ex = rng.choice(exercises)
            kw = sample(rng)
            seq = make_sequence(ex.start_angle_deg, ex.target_angle_deg, reps_per_condition,
                                noise_deg=noise, seed=rng.randrange(10**6), **kw)
            counter = RepetitionCounter(RepConfig(ex.start_angle_deg, ex.target_angle_deg, required_fraction=0.6))
            smoother = AngleSmoother()
            for t, a in seq:
                rep = counter.update(t, smoother.update(a) if a is not None else None)
                if rep is None:
                    continue
                f = rep_features(rep)
                rows.append({"participant_id": pid, "recording_id": f"{pid}-{label}", "exercise_id": ex.id,
                             "label": label, "source": "synthetic", **f})
    return rows
