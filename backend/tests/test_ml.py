import os
import tempfile

os.environ["ARVR_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/ml.db"

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.exercises.library import get_exercise
from app.main import app
from app.ml import dataset as ds
from app.ml.evaluation import metrics
from app.ml.inference import MLAssessor, ModelNotAvailable, model_status
from app.ml.synthetic_data import generate_dataset
from app.ml.training import train_and_evaluate


@pytest.fixture(scope="module")
def rows():
    return generate_dataset(n_participants=12, reps_per_condition=3, seed=1)


def test_synthetic_dataset_is_labelled_synthetic_and_covers_all_classes(rows):
    ds.validate_rows(rows)
    assert {r["source"] for r in rows} == {"synthetic"}
    assert {r["label"] for r in rows} == set(ds.LABELS) - {"posture_deviation", "incorrect_unspecified"}


def test_generation_is_deterministic():
    a = generate_dataset(3, 2, seed=5)
    b = generate_dataset(3, 2, seed=5)
    assert a == b


def test_split_has_no_participant_leakage(rows):
    train, test = ds.split_by_participant(rows, 0.3, seed=0)
    assert train and test
    assert {r["participant_id"] for r in train}.isdisjoint({r["participant_id"] for r in test})


def test_split_needs_two_participants():
    one = [r for r in generate_dataset(2, 1, seed=0) if r["participant_id"] == "S000"]
    with pytest.raises(ds.DatasetError):
        ds.split_by_participant(one)


def test_validation_rejects_bad_data(rows):
    with pytest.raises(ds.DatasetError):
        ds.validate_rows([])
    bad = dict(rows[0], label="made_up")
    with pytest.raises(ds.DatasetError):
        ds.validate_rows([bad])
    with pytest.raises(ds.DatasetError):
        ds.validate_rows([dict(rows[0], rom_deg=float("nan"))])
    with pytest.raises(ds.DatasetError):
        ds.validate_rows([dict(rows[0], exercise_id="nope")])
    missing = {k: v for k, v in rows[0].items() if k != "duration_s"}
    with pytest.raises(ds.DatasetError):
        ds.validate_rows([missing])


def test_csv_roundtrip(rows, tmp_path):
    p = tmp_path / "d.csv"
    ds.write_csv(rows, p)
    back = ds.read_csv(p)
    assert len(back) == len(rows) and back[0]["label"] == rows[0]["label"]


def test_metrics_hand_computed():
    y_true = ["acceptable", "acceptable", "too_fast", "too_fast"]
    y_pred = ["acceptable", "too_fast", "too_fast", "too_fast"]
    m = metrics(y_true, y_pred)
    assert m["accuracy"] == 0.75
    assert m["per_class"]["too_fast"]["precision"] == pytest.approx(2 / 3)
    assert m["per_class"]["too_fast"]["recall"] == 1.0
    assert m["per_class"]["acceptable"]["recall"] == 0.5
    i, j = ds.LABELS.index("acceptable"), ds.LABELS.index("too_fast")
    assert m["confusion_matrix"]["matrix"][i][j] == 1


def test_train_evaluate_save_and_infer(rows, tmp_path):
    res = train_and_evaluate(rows, tmp_path, seed=0, n_boot=20)
    ev = res["evaluation"]
    assert set(ev) >= {"majority_class", "rule_based", "random_forest", "_sizes"}
    assert ev["random_forest"]["accuracy"] >= ev["majority_class"]["accuracy"]
    assert res["metadata"]["synthetic_only"] is True
    assert "SYNTHETIC DATA ONLY" in (tmp_path / "reports" / res["version"] / "report.md").read_text(encoding="utf-8")
    assert model_status(tmp_path)["available"]

    clf = MLAssessor.load(tmp_path)
    ex = get_exercise("elbow_flexion")
    good = {"rom_deg": 95, "duration_s": 3.0, "peak_velocity_deg_s": 60, "mean_speed_deg_s": 35,
            "extra_reversals": 0, "peak_progress": 0.95, "reliability": 1.0}
    pred = clf.predict(good, ex)
    assert pred.model_version == res["version"] and abs(sum(pred.probabilities.values()) - 1) < 1e-6
    assert pred.label in set(ds.LABELS) | {"uncertain"}


def test_low_confidence_returns_uncertain(rows, tmp_path):
    train_and_evaluate(rows, tmp_path, n_boot=5)
    clf = MLAssessor.load(tmp_path)
    clf.clf.predict_proba = lambda X: [[1 / len(ds.LABELS)] * len(ds.LABELS)]  # flat distribution
    clf.clf.classes_ = ds.LABELS
    pred = clf.predict({"rom_deg": 1, "duration_s": 1, "peak_velocity_deg_s": 1, "mean_speed_deg_s": 1,
                        "extra_reversals": 0, "peak_progress": 0.5, "reliability": 1}, get_exercise("knee_flexion"))
    assert pred.uncertain and pred.label == "uncertain"


def test_committed_demo_model_is_loadable_and_clearly_synthetic():
    import json
    from pathlib import Path

    root = Path(settings.artifacts_dir)
    meta = json.loads((root / "models" / "synthetic-demo" / "metadata.json").read_text(encoding="utf-8"))
    assert meta["synthetic_only"] is True and meta["data_sources"] == ["synthetic"]
    assert "SYNTHETIC" in (root / "models" / "synthetic-demo" / "README.md").read_text(encoding="utf-8")
    clf = MLAssessor.load(root, version="synthetic-demo")
    good = {"rom_deg": 95, "duration_s": 3.0, "peak_velocity_deg_s": 60, "mean_speed_deg_s": 35,
            "extra_reversals": 0, "peak_progress": 0.95, "reliability": 1.0}
    pred = clf.predict(good, get_exercise("elbow_flexion"))
    assert abs(sum(pred.probabilities.values()) - 1) < 1e-6 and pred.label in set(ds.LABELS) | {"uncertain"}


def test_missing_model(tmp_path):
    with pytest.raises(ModelNotAvailable):
        MLAssessor.load(tmp_path)
    assert model_status(tmp_path)["available"] is False


def test_models_status_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path)
    with TestClient(app) as c:
        r = c.get("/api/models/status")
        assert r.status_code == 200 and r.json()["available"] is False
