"""Leave-one-participant-out (LOPO) evaluation for small real datasets.

Every participant is the test set once. Anything that is tuned (forest hyperparameters, the simple range-rule
threshold) is chosen using ONLY the training participants of that fold, via an inner leave-one-participant-out
search, so the held-out person never influences a choice (no test-set tuning).
"""
from collections import Counter

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score

from app.exercises.library import load_exercises
from app.ml.dataset import Row, validate_rows
from app.ml.evaluation import bootstrap_macro_f1_ci, metrics, rule_based_predict
from app.ml.features import FEATURE_NAMES, FEATURE_NAMES_POSTURE, POSTURE_FEATURES, ml_features

GRID = [(d, leaf) for d in (3, 6, None) for leaf in (1, 5, 20)]
THRESHOLDS = [round(t, 2) for t in np.arange(0.1, 1.31, 0.05)]
METHOD_TITLES = {
    "majority_class": "Majority class", "rule_based": "Rule-based (illustrative thresholds)",
    "rule_range_tuned": "Range rule, threshold tuned on training participants",
    "rf_base": "Random forest, angle features", "rf_base_tuned": "Random forest, angle features, tuned",
    "rf_posture": "Random forest, + posture features", "rf_posture_tuned": "Random forest, + posture features, tuned",
}


def _x(rows: list[Row], posture: bool) -> list[list[float]]:
    ex = load_exercises()
    return [ml_features(r, ex[str(r["exercise_id"])], posture) for r in rows]


def _y(rows: list[Row]) -> list[str]:
    return [str(r["label"]) for r in rows]


def _forest(params: tuple, seed: int) -> RandomForestClassifier:
    depth, leaf = params
    return RandomForestClassifier(n_estimators=150, max_depth=depth, min_samples_leaf=leaf, class_weight="balanced",
                                  random_state=seed, n_jobs=1)


def _select_params(train: list[Row], posture: bool, seed: int) -> tuple:
    """Inner LOPO over the training participants only; criterion = pooled balanced accuracy."""
    people = sorted({str(r["participant_id"]) for r in train})
    best, best_score = GRID[0], -1.0
    for params in GRID:
        yt, yp = [], []
        for held in people:
            tr = [r for r in train if r["participant_id"] != held]
            te = [r for r in train if r["participant_id"] == held]
            m = _forest(params, seed).fit(_x(tr, posture), _y(tr))
            yp += list(m.predict(_x(te, posture)))
            yt += _y(te)
        score = float(balanced_accuracy_score(yt, yp))
        if score > best_score + 1e-9:
            best, best_score = params, score
    return best


def _tune_range_rule(train: list[Row]) -> dict[str, float]:
    """Per exercise: threshold t on peak_progress, 'incorrect' if below it; maximise balanced accuracy on training."""
    out: dict[str, float] = {}
    for ex_id in {str(r["exercise_id"]) for r in train}:
        sub = [r for r in train if r["exercise_id"] == ex_id]
        truth = [r["label"] != "acceptable" for r in sub]
        best, best_score = 0.5, -1.0
        for t in THRESHOLDS:
            pred = [float(r["peak_progress"]) < t for r in sub]
            score = balanced_accuracy_score(truth, pred) if len(set(truth)) > 1 else 0.0
            if score > best_score + 1e-9:
                best, best_score = t, score
        out[ex_id] = best
    return out


def binary(y_true: list[str], y_pred: list[str]) -> dict:
    """acceptable vs anything else."""
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
    has_posture = all(k in rows[0] for k in POSTURE_FEATURES)
    variants = [("rf_base", False, False), ("rf_base_tuned", False, True)]
    if has_posture:
        variants += [("rf_posture", True, False), ("rf_posture_tuned", True, True)]

    ordered: list[Row] = []
    preds: dict[str, list[str]] = {"majority_class": [], "rule_range_tuned": [], **{v[0]: [] for v in variants}}
    chosen: dict[str, list] = {v[0]: [] for v in variants if v[2]}
    chosen["rule_range_tuned"] = []
    importances: dict[str, list[np.ndarray]] = {v[0]: [] for v in variants}
    for held in people:
        train = [r for r in rows if r["participant_id"] != held]
        test = [r for r in rows if r["participant_id"] == held]
        ordered += test
        preds["majority_class"] += [Counter(_y(train)).most_common(1)[0][0]] * len(test)
        thr = _tune_range_rule(train)
        chosen["rule_range_tuned"].append(thr)
        preds["rule_range_tuned"] += ["insufficient_range" if float(r["peak_progress"]) < thr[str(r["exercise_id"])]
                                      else "acceptable" for r in test]
        for name, posture, tune in variants:
            params = _select_params(train, posture, seed) if tune else (None, 1)
            if tune:
                chosen[name].append({"max_depth": params[0], "min_samples_leaf": params[1], "held_out": held})
            model = _forest(params, seed).fit(_x(train, posture), _y(train))
            preds[name] += list(model.predict(_x(test, posture)))
            importances[name].append(model.feature_importances_)
    preds["rule_based"] = rule_based_predict(ordered)

    y = _y(ordered)
    out: dict = {"participants": people, "n": len(y), "label_counts": dict(Counter(y)), "methods": {},
                 "tuning": chosen, "n_features": {"base": len(FEATURE_NAMES), "posture": len(FEATURE_NAMES_POSTURE)}}
    for name in [n for n in METHOD_TITLES if n in preds]:
        m = metrics(y, preds[name])
        m["macro_f1_ci95_participant_bootstrap"] = list(bootstrap_macro_f1_ci(ordered, preds[name], n_boot))
        m["binary_correct_vs_incorrect"] = binary(y, preds[name])
        out["methods"][name] = m
        out["methods"][name]["per_participant_accuracy"] = {
            p: float(np.mean([a == b for r, a, b in zip(ordered, y, preds[name]) if r["participant_id"] == p]))
            for p in people}
    names = {False: FEATURE_NAMES, True: FEATURE_NAMES_POSTURE}
    out["feature_importance"] = {
        n: dict(sorted(zip(names[n.startswith("rf_posture")], map(float, np.mean(v, axis=0))), key=lambda kv: -kv[1]))
        for n, v in importances.items() if v}
    return out


def render_lopo_report(ev: dict, source: str) -> str:
    L = ["# Leave-one-participant-out evaluation", "",
         f"Data: {source} | {ev['n']} repetitions from {len(ev['participants'])} participants "
         f"({', '.join(ev['participants'])}) | labels: {ev['label_counts']}", "",
         "> Small sample of healthy volunteers performing deliberate errors, one camera view per repetition, single-camera "
         "pose estimates. Preliminary: not clinical or patient data. Tuned methods choose hyperparameters/thresholds using only "
         "the training participants of each fold (nested), never the held-out person. With 5 participants the confidence "
         "intervals are wide and differences between methods should be read cautiously.", "",
         "## Three-class view (acceptable / insufficient_range / posture_deviation)", "",
         "| Method | Accuracy | Macro-F1 | Macro-F1 95% CI (participant bootstrap) |", "|---|---|---|---|"]
    for n, m in ev["methods"].items():
        lo, hi = m["macro_f1_ci95_participant_bootstrap"]
        L.append(f"| {METHOD_TITLES[n]} | {m['accuracy']:.3f} | {m['macro_f1']:.3f} | {lo:.3f} to {hi:.3f} |")
    L += ["", "## Binary view (acceptable vs any incorrect)", "",
          "| Method | Accuracy | Balanced acc. | Incorrect: precision | recall | F1 |", "|---|---|---|---|---|---|"]
    for n, m in ev["methods"].items():
        b = m["binary_correct_vs_incorrect"]
        L.append(f"| {METHOD_TITLES[n]} | {b['accuracy']:.3f} | {b['balanced_accuracy']:.3f} | {b['incorrect_precision']:.3f} | "
                 f"{b['incorrect_recall']:.3f} | {b['incorrect_f1']:.3f} |")
    L += ["", "## Per held-out participant (3-class accuracy)", "",
          "| Method | " + " | ".join(ev["participants"]) + " |", "|---|" + "---|" * len(ev["participants"])]
    for n, m in ev["methods"].items():
        L.append(f"| {METHOD_TITLES[n]} | " + " | ".join(f"{m['per_participant_accuracy'][p]:.3f}" for p in ev["participants"]) + " |")
    for name, imp in ev.get("feature_importance", {}).items():
        if name in ("rf_base_tuned", "rf_posture_tuned"):
            L += ["", f"## Feature importance (mean over folds): {METHOD_TITLES[name]}", ""]
            L += [f"- {k}: {v:.3f}" for k, v in list(imp.items())[:10]]
    for n in ("rf_base_tuned", "rf_posture_tuned"):
        if n in ev["methods"]:
            cm = ev["methods"][n]["confusion_matrix"]
            L += ["", f"Confusion matrix ({METHOD_TITLES[n]}; rows = true, cols = predicted; order: {', '.join(cm['labels'])})", "```"]
            L += [" ".join(f"{v:4d}" for v in row) for row in cm["matrix"]] + ["```"]
    return "\n".join(L) + "\n"
