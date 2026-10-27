"""External validation: train on one dataset, test on a different dataset with different people and setup.

Nothing about the test dataset is used for any choice. Models use fixed default hyperparameters, and the simple
range-rule threshold is fitted on the training dataset only. Binary task only (correct vs incorrect) because the
test set has no error-type labels. Only features computable from both skeleton sources are used.
"""
import random
from collections import Counter

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, confusion_matrix

from app.exercises.library import load_exercises
from app.ml.dataset import Row
from app.ml.features import FEATURE_NAMES, FEATURE_NAMES_POSTURE, ml_features

# computable from a motion-capture skeleton too: no ears/heels (head tilt, heel lift) and no MediaPipe depth estimates
COMMON_POSTURE = ["torso_tilt_dev_max", "torso_tilt_dev_mean", "shoulder_asym_dev_max", "elbow_bend_min_deg",
                  "lr_angle_asym_mean_deg", "knee_valgus_dev_max", "knee_over_toe_dev_max", "lower_body_exercise",
                  "posture_reliability"]
FEATURE_SETS = {"angle_only": FEATURE_NAMES, "angle_plus_posture": FEATURE_NAMES + COMMON_POSTURE}


def _x(rows: list[Row], names: list[str]) -> list[list[float]]:
    ex = load_exercises()
    idx = [FEATURE_NAMES_POSTURE.index(n) for n in names]
    out = []
    for r in rows:
        full = ml_features(r, ex[str(r["exercise_id"])], posture=True)
        out.append([full[i] for i in idx])
    return out


def _incorrect(rows: list[Row]) -> list[bool]:
    return [r["label"] != "acceptable" for r in rows]


def _scores(truth: list[bool], pred: list[bool]) -> dict:
    tp = sum(a and b for a, b in zip(truth, pred))
    fp = sum((not a) and b for a, b in zip(truth, pred))
    fn = sum(a and (not b) for a, b in zip(truth, pred))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"n": len(truth), "accuracy": sum(a == b for a, b in zip(truth, pred)) / len(truth),
            "balanced_accuracy": float(balanced_accuracy_score(truth, pred)) if len(set(truth)) > 1 else float("nan"),
            "incorrect_precision": prec, "incorrect_recall": rec,
            "incorrect_f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "confusion_matrix [[TN, FP], [FN, TP]]": confusion_matrix(truth, pred, labels=[False, True]).tolist()}


def _bootstrap_bal_acc(rows: list[Row], pred: list[bool], n_boot: int, seed: int = 0) -> list[float]:
    by: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        by.setdefault(str(r["participant_id"]), []).append(i)
    people, rng, vals = list(by), random.Random(seed), []
    truth = _incorrect(rows)
    for _ in range(n_boot):
        idx = [i for p in (rng.choice(people) for _ in people) for i in by[p]]
        t = [truth[i] for i in idx]
        if len(set(t)) > 1:
            vals.append(balanced_accuracy_score(t, [pred[i] for i in idx]))
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[max(0, int(0.975 * len(vals)) - 1)]] if vals else [float("nan")] * 2


def _fit_range_thresholds(train: list[Row]) -> dict[str, float]:
    out = {}
    for ex_id in {str(r["exercise_id"]) for r in train}:
        sub = [r for r in train if r["exercise_id"] == ex_id]
        truth = _incorrect(sub)
        best, best_s = 0.5, -1.0
        for t in np.arange(0.1, 1.31, 0.05):
            s = balanced_accuracy_score(truth, [float(r["peak_progress"]) < t for r in sub]) if len(set(truth)) > 1 else 0.0
            if s > best_s + 1e-9:
                best, best_s = float(t), s
        out[ex_id] = best
    return out


def _rf(seed: int) -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=200, class_weight="balanced", min_samples_leaf=5, random_state=seed, n_jobs=1)


def external_validation(train: list[Row], test: list[Row], seed: int = 0, n_boot: int = 300,
                        full_features: bool = False) -> dict:
    """full_features=True also evaluates the complete feature set (head tilt, heel lift, MediaPipe 3D cues); only
    meaningful when train and test skeletons both come from a pose estimator with those landmarks."""
    feature_sets = dict(FEATURE_SETS)
    if full_features:
        feature_sets["angle_plus_posture_full"] = FEATURE_NAMES_POSTURE
    shared = sorted({str(r["exercise_id"]) for r in train} & {str(r["exercise_id"]) for r in test})
    if not shared:
        raise ValueError("train and test sets share no exercise")
    train = [r for r in train if r["exercise_id"] in shared]
    test = [r for r in test if r["exercise_id"] in shared]
    truth = _incorrect(test)
    preds: dict[str, list[bool]] = {"majority_class (train prior)": [Counter(_incorrect(train)).most_common(1)[0][0]] * len(test)}
    thr = _fit_range_thresholds(train)
    preds["range_rule (threshold from train)"] = [float(r["peak_progress"]) < thr[str(r["exercise_id"])] for r in test]
    for name, feats in feature_sets.items():
        preds[f"rf_{name} (trained on train set)"] = list(_rf(seed).fit(_x(train, feats), _incorrect(train)).predict(_x(test, feats)))

    out: dict = {"shared_exercises": shared, "n_train": len(train), "n_test": len(test),
                 "train_participants": sorted({str(r["participant_id"]) for r in train}),
                 "test_participants": sorted({str(r["participant_id"]) for r in test}),
                 "test_incorrect_fraction": float(np.mean(truth)), "range_thresholds_from_train": thr, "methods": {}}
    for name, p in preds.items():
        m = _scores(truth, p)
        m["balanced_accuracy_ci95_participant_bootstrap"] = _bootstrap_bal_acc(test, p, n_boot, seed)
        m["by_exercise"] = {e: _scores([t for t, r in zip(truth, test) if r["exercise_id"] == e],
                                        [q for q, r in zip(p, test) if r["exercise_id"] == e]) for e in shared}
        m["by_participant_balanced_accuracy"] = {
            pid: _scores([t for t, r in zip(truth, test) if r["participant_id"] == pid],
                         [q for q, r in zip(p, test) if r["participant_id"] == pid])["balanced_accuracy"]
            for pid in out["test_participants"]}
        out["methods"][name] = m

    # reference: how separable the classes are WITHIN the test dataset (leave-one-participant-out, fixed params)
    ref = {}
    people = out["test_participants"]
    for name, feats in feature_sets.items():
        pred = [None] * len(test)
        for held in people:
            tr = [i for i, r in enumerate(test) if r["participant_id"] != held]
            te = [i for i, r in enumerate(test) if r["participant_id"] == held]
            if len({truth[i] for i in tr}) < 2:
                continue
            m = _rf(seed).fit(_x([test[i] for i in tr], feats), [truth[i] for i in tr])
            for i, p in zip(te, m.predict(_x([test[i] for i in te], feats))):
                pred[i] = bool(p)
        ok = [i for i, p in enumerate(pred) if p is not None]
        ref[f"rf_{name}"] = _scores([truth[i] for i in ok], [pred[i] for i in ok])
    out["in_domain_reference_loo_participant"] = ref
    return out


def render_external_report(ev: dict, train_name: str, test_name: str) -> str:
    L = [f"# External validation: train on {train_name}, test on {test_name}", "",
         f"Shared exercises: {', '.join(ev['shared_exercises'])} | train: {ev['n_train']} reps, "
         f"{len(ev['train_participants'])} participants | test: {ev['n_test']} reps, {len(ev['test_participants'])} participants "
         f"(incorrect fraction {ev['test_incorrect_fraction']:.2f})", "",
         "> Binary correct-vs-incorrect only. Fixed hyperparameters; nothing tuned on the test dataset. Different people, "
         "cameras and setup (compare the two data sources in the title: they may or may not share a skeleton source), so a "
         "drop from within-dataset results is expected and informative. Preliminary and non-clinical; "
         "wide intervals with few participants.", "",
         "| Method | Balanced acc. | 95% CI (participant bootstrap) | Accuracy | Incorrect: precision | recall | F1 |",
         "|---|---|---|---|---|---|---|"]
    for n, m in ev["methods"].items():
        lo, hi = m["balanced_accuracy_ci95_participant_bootstrap"]
        L.append(f"| {n} | {m['balanced_accuracy']:.3f} | {lo:.3f} to {hi:.3f} | {m['accuracy']:.3f} | "
                 f"{m['incorrect_precision']:.3f} | {m['incorrect_recall']:.3f} | {m['incorrect_f1']:.3f} |")
    L += ["", "## By exercise (balanced accuracy)", "", "| Method | " + " | ".join(ev["shared_exercises"]) + " |",
          "|---|" + "---|" * len(ev["shared_exercises"])]
    for n, m in ev["methods"].items():
        L.append(f"| {n} | " + " | ".join(f"{m['by_exercise'][e]['balanced_accuracy']:.3f}" for e in ev["shared_exercises"]) + " |")
    L += ["", "## By test participant (balanced accuracy, trained-on-train random forest with posture features)", ""]
    key = next(k for k in ev["methods"] if "angle_plus_posture" in k)
    L += [f"- {p}: {v:.3f}" for p, v in ev["methods"][key]["by_participant_balanced_accuracy"].items()]
    L += ["", f"## In-domain reference: leave-one-participant-out within {test_name} (same features, fixed params)", "",
          "| Features | Balanced acc. | Accuracy | Incorrect F1 |", "|---|---|---|---|"]
    for n, m in ev["in_domain_reference_loo_participant"].items():
        L.append(f"| {n} | {m['balanced_accuracy']:.3f} | {m['accuracy']:.3f} | {m['incorrect_f1']:.3f} |")
    return "\n".join(L) + "\n"

