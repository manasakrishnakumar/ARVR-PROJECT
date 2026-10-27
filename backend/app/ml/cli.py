"""python -m app.ml.cli generate|train  (run from the backend folder)"""
import argparse
import json
from pathlib import Path

from app.core.config import settings
from app.ml.dataset import read_csv, write_csv
from app.ml.synthetic_data import generate_dataset
from app.ml.training import train_and_evaluate


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="write a SYNTHETIC labelled dataset CSV")
    g.add_argument("--out", type=Path, default=settings.artifacts_dir.parent / "datasets" / "sample" / "synthetic_reps.csv")
    g.add_argument("--participants", type=int, default=20)
    g.add_argument("--seed", type=int, default=0)
    t = sub.add_parser("train", help="train + evaluate on a labelled repetition CSV")
    t.add_argument("--data", type=Path, required=True)
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--artifacts", type=Path, default=settings.artifacts_dir)
    a = ap.parse_args()

    if a.cmd == "generate":
        rows = generate_dataset(a.participants, seed=a.seed)
        write_csv(rows, a.out)
        print(f"Wrote {len(rows)} SYNTHETIC rows to {a.out}")
    else:
        res = train_and_evaluate(read_csv(a.data), a.artifacts, seed=a.seed)
        ev = res["evaluation"]
        print(f"Model {res['version']}\nReport: {Path(res['report_dir']) / 'report.md'}")
        for name in ("majority_class", "rule_based", "random_forest"):
            print(f"  {name:15s} accuracy={ev[name]['accuracy']:.3f} macro_f1={ev[name]['macro_f1']:.3f}")
        print(json.dumps(ev["_sizes"]))


if __name__ == "__main__":
    main()
