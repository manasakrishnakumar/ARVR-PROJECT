import random

import pytest

from app.feature_extraction.posture import POSTURE_ZEROS
from app.ml.external import external_validation, render_external_report
from app.ml.synthetic_data import generate_dataset


def _rows(n, seed, prefix):
    out = []
    for r in generate_dataset(n_participants=n, reps_per_condition=3, seed=seed):
        out.append({**r, **POSTURE_ZEROS, "participant_id": prefix + str(r["participant_id"])})
    return out


def test_runs_and_reports_all_parts():
    ev = external_validation(_rows(8, 1, "tr"), _rows(5, 2, "te"), n_boot=10)
    assert ev["n_test"] > 0 and set(ev["train_participants"]).isdisjoint(ev["test_participants"])
    assert len(ev["methods"]) == 4 and "in_domain_reference_loo_participant" in ev
    text = render_external_report(ev, "train-set", "test-set")
    assert "External validation" in text and "Preliminary" in text


def test_test_labels_never_influence_predictions():
    train, test = _rows(8, 1, "tr"), _rows(5, 2, "te")
    a = external_validation(train, test, n_boot=5)
    flipped = [{**r, "label": random.Random(i).choice(["acceptable", "too_fast"])} for i, r in enumerate(test)]
    b = external_validation(train, flipped, n_boot=5)
    for name in a["methods"]:
        pos = lambda m: m["confusion_matrix [[TN, FP], [FN, TP]]"]
        pa, pb = pos(a["methods"][name]), pos(b["methods"][name])
        assert pa[0][1] + pa[1][1] == pb[0][1] + pb[1][1], name  # same number of 'incorrect' predictions


def test_no_shared_exercise_is_an_error():
    train = [r for r in _rows(8, 1, "tr") if r["exercise_id"] == "elbow_flexion"]
    test = [r for r in _rows(5, 2, "te") if r["exercise_id"] != "elbow_flexion"]
    if train and test:
        with pytest.raises(ValueError):
            external_validation(train, test, n_boot=3)
