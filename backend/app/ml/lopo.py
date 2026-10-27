"""Leave-one-participant-out evaluation for small real datasets (every participant is the test set once)."""
from collections import Counter

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score

from app.exercises.library import load_exercises
from app.ml.dataset import Row, validate_rows
from app.ml.evaluation import bootstrap_macro_f1_ci, metrics, rule_based_predict
from app.ml.features import ml_features


def _x(rows: list[Row]) -> list[list[float]]:
    ex = load_exercises()
    return [ml_features(r, ex[str(r["exercise_id"])]) for r in rows]


def binary(y_true: list[str], y_pred: list[str]) -> dict:
    """acceptable vs anything else (rule 'insufficient_data' counts as not acceptable)."""
    t = [l != "acceptable" for l in y_true]
    p = [l != "acceptable" for l in y_pred]
    tp = sum(a and b for a, b in zip(t, p))
    fp = sum((not a) and b for a, b in zip(t, p))
    fn = sum(a and (not b) for a, b in zip(t, p))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"accuracy": sum(a == b for a, b in zip(t, p)) / len(t), "balanced_accuracy": float(balanced_accuracy_score(t, p)),
            "incorrect_precision": prec, "incorrect_recall": rec,
            "incorrect_f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0}


def run_lopo(rows: list[Row], seed: int = 0, n_boot: int = 300) -> dict:
    validate_rows(rows)
    people = sorted({str(r["participant_id"]) for r in rows})
    if len(people) < 3:
        raise ValueError("leave-one-participant-out needs at least 3 participants")
    ordered, y_rf, y_maj = [], [], []
    for held in people:
        train = [r for r in rows if r["participant_id"] != held]
        test = [r for r in rows if r["participant_id"] == held]
        clf = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=seed, n_jobs=1)
        clf.fit(_x(train), [str(r["label"]) for r in train])
        y_rf += list(clf.predict(_x(test)))
        y_maj += [Counter(str(r["label"]) for r in train).most_common(1)[0][0]] * len(test)
        ordered += test
    y = [str(r["label"]) for r in ordered]
    preds = {"majority_class": y_maj, "rule_based": rule_based_predict(ordered), "random_forest": y_rf}
    out: dict = {"participants": people, "n": len(y), "label_counts": dict(Counter(y)), "methods": {}}
    for name, yp in preds.items():
        m = metrics(y, yp)
        m["macro_f1_ci95_participant_bootstrap"] = list(bootstrap_macro_f1_ci(ordered, yp, n_boot))
        m["binary_correct_vs_incorrect"] = binary(y, yp)
        out["methods"][name] = m
    out["per_participant_rf_accuracy"] = {
        p: sum(a == b for (r, a, b) in zip(ordered, y, y_rf) if r["participant_id"] == p)
        / max(1, sum(r["participant_id"] == p for r in ordered)) for p in people}
    return out


def render_lopo_report(ev: dict, source: str) -> str:
    L = [f"# Leave-one-participant-out evaluation", "",
         f"Data: {source} | {ev['n']} repetitions from {len(ev['participants'])} participants "
         f"({', '.join(ev['participants'])}) | labels: {ev['label_counts']}", "",
         "> Small sample of healthy volunteers performing deliberate errors, one camera view per repetition. "
         "Preliminary: not clinical data, not patient data, and a single-joint-angle feature set cannot see most posture errors. "
         "Rule-based thresholds are the *illustrative, untuned* defaults.", "",
         "## Three-class view (acceptable / insufficient_range / posture_deviation)", "",
         "| Method | Accuracy | Macro-F1 | Macro-F1 95% CI (participant bootstrap) |", "|---|---|---|---|"]
    for n, m in ev["methods"].items():
        lo, hi = m["macro_f1_ci95_participant_bootstrap"]
        L.append(f"| {n} | {m['accuracy']:.3f} | {m['macro_f1']:.3f} | {lo:.3f} to {hi:.3f} |")
    L += ["", "## Binary view (acceptable vs any incorrect)", "",
          "| Method | Accuracy | Balanced acc. | Incorrect: precision | recall | F1 |", "|---|---|---|---|---|---|"]
    for n, m in ev["methods"].items():
        b = m["binary_correct_vs_incorrect"]
        L.append(f"| {n} | {b['accuracy']:.3f} | {b['balanced_accuracy']:.3f} | {b['incorrect_precision']:.3f} | "
                 f"{b['incorrect_recall']:.3f} | {b['incorrect_f1']:.3f} |")
    L += ["", "## Random forest, per held-out participant (3-class accuracy)", ""]
    L += [f"- {p}: {a:.3f}" for p, a in ev["per_participant_rf_accuracy"].items()]
    for n in ("rule_based", "random_forest"):
        cm = ev["methods"][n]["confusion_matrix"]
        L += ["", f"Confusion matrix ({n}; rows = true, cols = predicted; order: {', '.join(cm['labels'])})", "```"]
        L += [" ".join(f"{v:4d}" for v in row) for row in cm["matrix"]] + ["```"]
    return "\n".join(L) + "\n"
