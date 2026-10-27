"""python -m app.ml.cli generate|train  (run from the backend folder)"""
import argparse
import json
from pathlib import Path

from app.core.config import settings
from app.ml.dataset import read_csv, write_csv
from app.ml.external import external_validation, render_external_report
from app.ml.lopo import render_lopo_report, run_lopo
from app.ml.rehab24 import import_rehab24
from app.ml.rehab26 import import_rehab26
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
    r = sub.add_parser("import-rehab26", help="convert REHAB26-ViewAngles (CC BY-NC) into a repetition CSV")
    r.add_argument("--root", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab26")
    r.add_argument("--out", type=Path, default=None)
    r.add_argument("--aspect", type=float, default=0.5625, help="video width/height used to equalise x and y scales")
    r24 = sub.add_parser("import-rehab24", help="convert REHAB24-6 (CC BY-NC, mocap skeletons) into a repetition CSV")
    r24.add_argument("--root", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab24")
    r24.add_argument("--out", type=Path, default=None)
    ex = sub.add_parser("external", help="train on one repetition CSV, test on another (binary, nothing tuned on test)")
    ex.add_argument("--train", type=Path, required=True)
    ex.add_argument("--test", type=Path, required=True)
    ex.add_argument("--report", type=Path, required=True)
    ex.add_argument("--seed", type=int, default=0)
    lo = sub.add_parser("lopo", help="leave-one-participant-out evaluation on a repetition CSV")
    lo.add_argument("--data", type=Path, required=True)
    lo.add_argument("--seed", type=int, default=0)
    lo.add_argument("--report", type=Path, default=None)
    a = ap.parse_args()

    if a.cmd == "import-rehab26":
        rows, stats = import_rehab26(a.root, aspect=a.aspect)
        out = a.out or a.root / "reps.csv"
        write_csv(rows, out)
        print(f"Wrote {len(rows)} repetitions to {out}\n{json.dumps(stats)}")
    elif a.cmd == "import-rehab24":
        rows, stats = import_rehab24(a.root)
        out = a.out or a.root / "reps.csv"
        write_csv(rows, out)
        print(f"Wrote {len(rows)} repetitions to {out}\n{json.dumps(stats)}")
    elif a.cmd == "external":
        tr, te = read_csv(a.train), read_csv(a.test)
        ev = external_validation(tr, te, seed=a.seed)
        a.report.write_text(render_external_report(ev, str(tr[0]["source"]), str(te[0]["source"])), encoding="utf-8")
        print(f"Report: {a.report}")
        for n, m in ev["methods"].items():
            lo_, hi_ = m["balanced_accuracy_ci95_participant_bootstrap"]
            print(f"  {n:45s} balanced_acc={m['balanced_accuracy']:.3f} (CI {lo_:.3f}-{hi_:.3f}) incorrect_f1={m['incorrect_f1']:.3f}")
        for n, m in ev["in_domain_reference_loo_participant"].items():
            print(f"  in-domain reference {n:20s} balanced_acc={m['balanced_accuracy']:.3f}")
    elif a.cmd == "lopo":
        rows = read_csv(a.data)
        ev = run_lopo(rows, seed=a.seed)
        report = a.report or a.data.with_name("lopo_report.md")
        report.write_text(render_lopo_report(ev, str(rows[0]["source"])), encoding="utf-8")
        print(f"Report: {report}")
        for n, m in ev["methods"].items():
            b = m["binary_correct_vs_incorrect"]
            print(f"  {n:18s} 3-class acc={m['accuracy']:.3f} macro_f1={m['macro_f1']:.3f} | "
                  f"binary balanced_acc={b['balanced_accuracy']:.3f} incorrect_f1={b['incorrect_f1']:.3f}")
    elif a.cmd == "generate":
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
