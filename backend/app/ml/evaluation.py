"""Compare majority-class, rule-based and ML classifiers on a participant-held-out test set."""
import random
from collections import Counter

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from app.exercise_assessment.rules import assess_rep
from app.exercises.library import load_exercises
from app.ml.dataset import LABELS, Row


def rule_based_predict(rows: list[Row], difficulty: int = 1) -> list[str]:
    ex = load_exercises()
    return [assess_rep(ex[str(r["exercise_id"])], difficulty, {k: float(v) for k, v in r.items()
                                                                 if k not in ("participant_id", "recording_id",
                                                                              "exercise_id", "label", "source")}).label
            for r in rows]


def metrics(y_true: list[str], y_pred: list[str]) -> dict:
    p, r, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, zero_division=0)
    return {
        "n": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1.mean()),
        "per_class": {l: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f1[i]), "support": int(support[i])}
                      for i, l in enumerate(LABELS)},
        "confusion_matrix": {"labels": LABELS, "matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist()},
    }


def bootstrap_macro_f1_ci(rows: list[Row], y_pred: list[str], n_boot: int = 300, seed: int = 0) -> tuple[float, float]:
    """95% CI of macro-F1, resampling whole participants (rows within a participant are correlated)."""
    by_p: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        by_p.setdefault(str(r["participant_id"]), []).append(i)
    people = list(by_p)
    rng, scores = random.Random(seed), []
    for _ in range(n_boot):
        idx = [i for p in (rng.choice(people) for _ in people) for i in by_p[p]]
        yt = [str(rows[i]["label"]) for i in idx]
        scores.append(metrics(yt, [y_pred[i] for i in idx])["macro_f1"])
    scores.sort()
    return scores[int(0.025 * n_boot)], scores[int(0.975 * n_boot) - 1]


def compare(train: list[Row], test: list[Row], ml_pred: list[str], n_boot: int = 300) -> dict:
    y = [str(r["label"]) for r in test]
    majority = Counter(str(r["label"]) for r in train).most_common(1)[0][0]
    preds = {"majority_class": [majority] * len(test), "rule_based": rule_based_predict(test), "random_forest": ml_pred}
    out = {}
    for name, yp in preds.items():
        m = metrics(y, yp)
        lo, hi = bootstrap_macro_f1_ci(test, yp, n_boot)
        m["macro_f1_ci95_participant_bootstrap"] = [lo, hi]
        out[name] = m
    out["_sizes"] = {
        "train_rows": len(train), "test_rows": len(test),
        "train_participants": len({r["participant_id"] for r in train}),
        "test_participants": len({r["participant_id"] for r in test}),
    }
    return out
