"""SIMULATION of the adaptive controller against fixed-difficulty baselines.

This checks how the controller BEHAVES under explicitly stated, made-up user models (stable, improving, fluctuating,
declining ability). It cannot show that adaptive difficulty helps real people: the outcomes follow from the assumptions
below. What it can show: the policy stays inside its safety limits, reacts in the intended direction, does not oscillate,
and spends fewer sessions at badly matched levels than a fixed level under the same assumptions.

Assumptions (all arbitrary and stated): a user has an ability a in [0, 1]; at level L a repetition is acceptable with
probability sigmoid(10 * (a - d_L)) where d = {1: 0.35, 2: 0.55, 3: 0.75}; acceptable repetitions score ~0.95 and count;
unacceptable ones score ~0.5 and do not count; 5% of repetitions are unreliable.
"""
import argparse
import json
import math
import random
import statistics
from pathlib import Path

from app.exercises.library import get_exercise
from app.personalization.controller import AdaptiveConfig, HistoryItem, RepObs, recommend

DEMAND = {1: 0.35, 2: 0.55, 3: 0.75}
MODELS = ("stable", "improving", "fluctuating", "declining")
POLICIES = ("fixed_level_1", "fixed_level_2", "fixed_level_3", "adaptive")
LEVELS = get_exercise("elbow_flexion").difficulty_levels  # 3 levels; reps per session 5 / 8 / 10


def p_acceptable(ability: float, level: int) -> float:
    return 1 / (1 + math.exp(-10 * (ability - DEMAND[level])))


def abilities(model: str, rng: random.Random, n: int) -> list[float]:
    if model == "stable":
        a = rng.uniform(0.3, 0.9)
        return [a] * n
    if model == "improving":
        a = rng.uniform(0.2, 0.6)
        return [min(1.0, a + 0.012 * i) for i in range(n)]
    if model == "fluctuating":
        a = rng.uniform(0.35, 0.8)
        return [min(1.0, max(0.0, a + rng.gauss(0, 0.08))) for _ in range(n)]
    if model == "declining":
        a = rng.uniform(0.6, 0.9)
        return [max(0.1, a - 0.012 * i) for i in range(n)]
    raise ValueError(model)


def session_reps(rng: random.Random, ability: float, level: int) -> list[RepObs]:
    reps = []
    for _ in range(int(LEVELS[str(level)]["target_reps"])):
        ok = rng.random() < p_acceptable(ability, level)
        reps.append(RepObs(label="acceptable" if ok else "insufficient_range", reliable=rng.random() > 0.05, counted=ok,
                           score=min(1.0, max(0.0, rng.gauss(0.95, 0.04) if ok else rng.gauss(0.5, 0.12))),
                           peak_progress=max(0.0, rng.gauss(0.9 if ok else 0.55, 0.05))))
    return reps


def run_user(cfg: AdaptiveConfig, policy: str, model: str, seed: int, n_sessions: int = 40) -> dict:
    rng = random.Random(seed)
    ab = abilities(model, rng, n_sessions)
    level = {"fixed_level_1": 1, "fixed_level_2": 2, "fixed_level_3": 3}.get(policy, cfg.default_level)
    history: list[HistoryItem] = []
    levels, too_hard, too_easy, pauses, violations = [], 0, 0, 0, 0
    for a in ab:
        p = p_acceptable(a, level)
        too_hard += p < 0.5
        too_easy += p > 0.95 and level < 3
        levels.append(level)
        if policy == "adaptive":
            r = recommend(cfg, LEVELS, level, session_reps(rng, a, level), history)
            pauses += r.action == "pause"
            violations += not (1 <= r.next_level <= 3 and abs(r.next_level - level) <= 1 and (r.next_level <= level or r.classification == "good"))
            history.insert(0, HistoryItem(level=level, classification=r.classification, action=r.action))
            level = r.next_level
    changes = sum(1 for x, y in zip(levels, levels[1:]) if x != y)
    moves = [y - x for x, y in zip(levels, levels[1:]) if x != y]
    reversals = sum(1 for x, y in zip(moves, moves[1:]) if x * y < 0)
    n = len(ab)
    return {"too_hard_share": too_hard / n, "too_easy_share": too_easy / n, "mismatch_share": (too_hard + too_easy) / n,
            "level_changes": changes, "direction_reversals": reversals, "pause_share": pauses / n,
            "final_level": levels[-1], "violations": violations}


def paired_bootstrap_diff(a: list[float], b: list[float], n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Mean of (a - b) over matched users with a 95% bootstrap interval."""
    d = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(d, k=len(d))) for _ in range(n_boot))
    return statistics.fmean(d), means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


def simulate(n_users: int = 200, n_sessions: int = 40, seed: int = 0) -> dict:
    cfg = AdaptiveConfig.load()
    out: dict = {"n_users_per_model": n_users, "n_sessions": n_sessions, "assumptions": __doc__, "models": {}}
    for model in MODELS:
        res = {pol: [run_user(cfg, pol, model, seed * 100003 + u, n_sessions) for u in range(n_users)] for pol in POLICIES}
        summary = {pol: {k: statistics.fmean(r[k] for r in rs) for k in rs[0]} for pol, rs in res.items()}
        best_fixed = min((p for p in POLICIES if p != "adaptive"), key=lambda p: summary[p]["mismatch_share"])
        diff, lo, hi = paired_bootstrap_diff([r["mismatch_share"] for r in res["adaptive"]],
                                             [r["mismatch_share"] for r in res[best_fixed]])
        out["models"][model] = {"policies": summary, "best_fixed_by_mismatch": best_fixed,
                                "adaptive_minus_best_fixed_mismatch_share": {"mean": diff, "ci95": [lo, hi]},
                                "safety_violations_total": sum(r["violations"] for r in res["adaptive"])}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--users", type=int, default=200)
    ap.add_argument("--sessions", type=int, default=40)
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()
    res = simulate(a.users, a.sessions)
    for m, v in res["models"].items():
        d = v["adaptive_minus_best_fixed_mismatch_share"]
        print(f"{m:12s} best fixed={v['best_fixed_by_mismatch']:14s} mismatch adaptive={v['policies']['adaptive']['mismatch_share']:.2f} "
              f"fixed={v['policies'][v['best_fixed_by_mismatch']]['mismatch_share']:.2f} diff={d['mean']:+.2f} CI[{d['ci95'][0]:+.2f},{d['ci95'][1]:+.2f}] "
              f"changes={v['policies']['adaptive']['level_changes']:.1f} reversals={v['policies']['adaptive']['direction_reversals']:.1f} violations={v['safety_violations_total']}")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"kind": "simulation", "title": "Adaptive vs fixed difficulty: SIMULATION of controller behaviour",
                                      "caveat": "Made-up user models with stated assumptions. Verifies safety and behaviour of the policy; says nothing about "
                                                "whether adaptive difficulty helps real people.", "data": res}, indent=2), encoding="utf-8")
        print(f"Results JSON: {a.json}")


if __name__ == "__main__":
    main()
