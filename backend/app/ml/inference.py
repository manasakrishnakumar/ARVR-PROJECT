"""Load a saved model and classify one repetition. Returns an explicit 'uncertain' state when unsure."""
import json
from dataclasses import dataclass
from pathlib import Path

import joblib

from app.exercises.library import Exercise
from app.ml.features import ml_features

UNCERTAIN_BELOW = 0.5


class ModelNotAvailable(RuntimeError):
    pass


@dataclass
class Prediction:
    label: str  # "uncertain" when max class probability < UNCERTAIN_BELOW
    confidence: float
    probabilities: dict[str, float]
    uncertain: bool
    model_version: str


def latest_version(artifacts_dir: Path) -> str | None:
    f = artifacts_dir / "models" / "LATEST"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def model_status(artifacts_dir: Path) -> dict:
    v = latest_version(artifacts_dir)
    meta_path = artifacts_dir / "models" / v / "metadata.json" if v else None
    if not v or not meta_path or not meta_path.exists() or not (meta_path.parent / "model.joblib").exists():
        return {"available": False, "detail": "No trained model found. Run scripts\\train_model.ps1.", "metadata": None}
    return {"available": True, "detail": "ok", "metadata": json.loads(meta_path.read_text(encoding="utf-8"))}


class MLAssessor:
    def __init__(self, clf, version: str):
        self.clf, self.version = clf, version

    @classmethod
    def load(cls, artifacts_dir: Path, version: str | None = None) -> "MLAssessor":
        version = version or latest_version(artifacts_dir)
        path = artifacts_dir / "models" / version / "model.joblib" if version else None
        if not path or not path.exists():
            raise ModelNotAvailable("no trained model available")
        return cls(joblib.load(path), version)

    def predict(self, raw: dict, ex: Exercise) -> Prediction:
        proba = self.clf.predict_proba([ml_features(raw, ex)])[0]
        probs = {str(c): float(p) for c, p in zip(self.clf.classes_, proba)}
        best = max(probs, key=probs.get)  # type: ignore[arg-type]
        unsure = probs[best] < UNCERTAIN_BELOW
        return Prediction("uncertain" if unsure else best, probs[best], probs, unsure, self.version)
