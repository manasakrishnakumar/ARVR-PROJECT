"""Repetition-level dataset: schema, validation, CSV I/O and participant-level splitting.

One row = one repetition. Rows from the same participant are highly correlated, so train/test
splits are made by participant_id, never by random row (prevents leakage).
"""
import csv
import math
import random
from pathlib import Path

from app.exercises.library import load_exercises

LABELS = ["acceptable", "insufficient_range", "incomplete_repetition", "too_fast", "uncontrolled", "insufficient_data"]
META_COLUMNS = ["participant_id", "recording_id", "exercise_id", "label", "source"]
RAW_FEATURES = ["rom_deg", "duration_s", "peak_velocity_deg_s", "mean_speed_deg_s", "extra_reversals",
                "peak_progress", "reliability"]
COLUMNS = META_COLUMNS + RAW_FEATURES

Row = dict[str, str | float]


class DatasetError(ValueError):
    pass


def validate_rows(rows: list[Row]) -> None:
    if not rows:
        raise DatasetError("dataset is empty")
    problems: list[str] = []
    exercises = load_exercises()
    for i, r in enumerate(rows):
        missing = [c for c in COLUMNS if c not in r or r[c] in ("", None)]
        if missing:
            problems.append(f"row {i}: missing {missing}")
            continue
        if r["label"] not in LABELS:
            problems.append(f"row {i}: unknown label {r['label']!r}")
        if r["exercise_id"] not in exercises:
            problems.append(f"row {i}: unknown exercise {r['exercise_id']!r}")
        for c in RAW_FEATURES:
            try:
                if not math.isfinite(float(r[c])):
                    raise ValueError
            except (TypeError, ValueError):
                problems.append(f"row {i}: non-finite {c}={r[c]!r}")
    if problems:
        raise DatasetError(f"{len(problems)} invalid rows; first: {problems[:5]}")


def write_csv(rows: list[Row], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> list[Row]:
    with path.open(newline="", encoding="utf-8") as f:
        rows: list[Row] = []
        for r in csv.DictReader(f):
            rows.append({k: (float(v) if k in RAW_FEATURES else v) for k, v in r.items()})
    validate_rows(rows)
    return rows


def split_by_participant(rows: list[Row], test_fraction: float = 0.3, seed: int = 0) -> tuple[list[Row], list[Row]]:
    people = sorted({str(r["participant_id"]) for r in rows})
    if len(people) < 2:
        raise DatasetError("need at least 2 participants to split without leakage")
    rng = random.Random(seed)
    rng.shuffle(people)
    n_test = min(len(people) - 1, max(1, round(len(people) * test_fraction)))
    test_ids = set(people[:n_test])
    train = [r for r in rows if r["participant_id"] not in test_ids]
    test = [r for r in rows if r["participant_id"] in test_ids]
    return train, test
