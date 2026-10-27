"""Train the Random Forest, compare it with the baselines, and persist model + report with a version."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn
from sklearn.ensemble import RandomForestClassifier

from app.exercises.library import load_exercises
from app.ml.dataset import LABELS, DatasetError, Row, split_by_participant, validate_rows
from app.ml.evaluation import compare
from app.ml.features import FEATURE_NAMES, ml_features


def _matrix(rows: list[Row]) -> list[list[float]]:
    ex = load_exercises()
    return [ml_features(r, ex[str(r["exercise_id"])]) for r in rows]


def _data_hash(rows: list[Row]) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update(json.dumps(r, sort_keys=True, default=str).encode())
    return h.hexdigest()


def train_and_evaluate(rows: list[Row], artifacts_dir: Path, seed: int = 0, test_fraction: float = 0.3,
                       n_boot: int = 300) -> dict:
    validate_rows(rows)
    train, test = split_by_participant(rows, test_fraction, seed)
    if len({r["label"] for r in train}) < 2:
        raise DatasetError("training split contains fewer than 2 classes")

    clf = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=seed, n_jobs=1)
    clf.fit(_matrix(train), [str(r["label"]) for r in train])
    evaluation = compare(train, test, list(clf.predict(_matrix(test))), n_boot)

    sources = sorted({str(r["source"]) for r in rows})
    digest = _data_hash(rows)
    version = f"rf-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{digest[:8]}"
    meta = {
        "version": version, "created_utc": datetime.now(timezone.utc).isoformat(), "algorithm": "RandomForestClassifier",
        "sklearn_version": sklearn.__version__, "features": FEATURE_NAMES, "classes": list(clf.classes_),
        "all_labels": LABELS, "data_sources": sources, "synthetic_only": sources == ["synthetic"],
        "data_sha256": digest, "n_rows": len(rows), "seed": seed, "split": "by participant_id",
        "evaluation_sizes": evaluation["_sizes"],
        "feature_importance": dict(zip(FEATURE_NAMES, map(float, clf.feature_importances_))),
        "note": "Research prototype classifier; not validated on real human movement unless data_sources says otherwise.",
    }
    model_dir = artifacts_dir / "models" / version
    report_dir = artifacts_dir / "reports" / version
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, model_dir / "model.joblib")
    (model_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (artifacts_dir / "models" / "LATEST").write_text(version, encoding="utf-8")
    (report_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    (report_dir / "report.md").write_text(render_report(meta, evaluation), encoding="utf-8")
    return {"version": version, "model_dir": str(model_dir), "report_dir": str(report_dir),
            "evaluation": evaluation, "metadata": meta}


def render_report(meta: dict, ev: dict) -> str:
    s = ev["_sizes"]
    lines = [f"# Evaluation report {meta['version']}", ""]
    if meta["synthetic_only"]:
        lines += ["> **SYNTHETIC DATA ONLY.** Labels come from a generator, not human annotation. These numbers only show the "
                  "pipeline runs; they say nothing about accuracy on real people, and the generator mirrors the rule thresholds, "
                  "so they cannot show which method is better in practice.", ""]
    lines += [f"Data sources: {', '.join(meta['data_sources'])} | rows: {meta['n_rows']} | split: by participant "
              f"({s['train_participants']} train / {s['test_participants']} test participants; "
              f"{s['train_rows']} / {s['test_rows']} rows) | seed {meta['seed']}", "",
              "| Method | Accuracy | Macro-F1 | Macro-F1 95% CI (participant bootstrap) |", "|---|---|---|---|"]
    for name in ("majority_class", "rule_based", "random_forest"):
        m = ev[name]
        lo, hi = m["macro_f1_ci95_participant_bootstrap"]
        lines.append(f"| {name} | {m['accuracy']:.3f} | {m['macro_f1']:.3f} | {lo:.3f} to {hi:.3f} |")
    for name in ("rule_based", "random_forest"):
        m = ev[name]
        lines += ["", f"## Per-class: {name}", "", "| Class | Precision | Recall | F1 | Support |", "|---|---|---|---|---|"]
        for c, v in m["per_class"].items():
            lines.append(f"| {c} | {v['precision']:.2f} | {v['recall']:.2f} | {v['f1']:.2f} | {v['support']} |")
        cm = m["confusion_matrix"]
        lines += ["", f"Confusion matrix ({name}; rows = true, columns = predicted; order: {', '.join(cm['labels'])})", "",
                  "```"] + [" ".join(f"{v:4d}" for v in row) for row in cm["matrix"]] + ["```"]
    return "\n".join(lines) + "\n"
