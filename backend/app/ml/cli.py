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


def _write_result(path: Path | None, kind: str, title: str, caveat: str, data: dict) -> None:
    """Aggregate metrics only (never raw data), for the research page and for the thesis tables."""
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"kind": kind, "title": title, "caveat": caveat, "data": data}, indent=2), encoding="utf-8")
    print(f"Results JSON: {path}")


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
    t.add_argument("--json", type=Path, default=None, help="also write aggregate results as JSON (used by the research page)")
    r = sub.add_parser("import-rehab26", help="convert REHAB26-ViewAngles (CC BY-NC) into a repetition CSV")
    r.add_argument("--root", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab26")
    r.add_argument("--out", type=Path, default=None)
    r.add_argument("--aspect", type=float, default=0.5625, help="video width/height used to equalise x and y scales")
    r24 = sub.add_parser("import-rehab24", help="convert REHAB24-6 (CC BY-NC, mocap skeletons) into a repetition CSV")
    r24.add_argument("--root", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab24")
    r24.add_argument("--out", type=Path, default=None)
    fv = sub.add_parser("fetch-rehab24-videos", help="download only the REHAB24-6 videos needed (HTTP range requests)")
    fv.add_argument("--root", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab24")
    fv.add_argument("--workers", type=int, default=4)
    xv = sub.add_parser("extract-rehab24-videos", help="run MediaPipe Pose on the needed REHAB24-6 repetition frames")
    xv.add_argument("--root", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab24")
    xv.add_argument("--model", type=Path, default=settings.artifacts_dir.parent / "frontend" / "public" / "models" / "pose_landmarker_full.task")
    xv.add_argument("--limit", type=int, default=0, help="process only the first N recordings (0 = all)")
    io_ = sub.add_parser("import-own", help="convert recordings made with the app's Record data page into repetition rows")
    io_.add_argument("--dir", type=Path, default=settings.artifacts_dir.parent / "datasets" / "own")
    io_.add_argument("--out", type=Path, default=None)
    io_.add_argument("--include-synthetic", action="store_true", help="also import recordings flagged synthetic (pipeline tests only)")
    ce = sub.add_parser("count-eval", help="repetition counting vs the datasets' labelled repetition boundaries")
    ce.add_argument("--rehab26", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab26")
    ce.add_argument("--rehab24", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab24")
    ce.add_argument("--json", type=Path, default=None)
    ae = sub.add_parser("angle-eval", help="MediaPipe joint-angle error vs motion capture on REHAB24-6 (needs extracted videos)")
    ae.add_argument("--root", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab24")
    ae.add_argument("--json", type=Path, default=None)
    iv = sub.add_parser("import-rehab24-video", help="convert MediaPipe output on the REHAB24-6 videos into a repetition CSV")
    iv.add_argument("--root", type=Path, default=settings.artifacts_dir.parent / "datasets" / "external" / "rehab24")
    iv.add_argument("--out", type=Path, default=None)
    ex = sub.add_parser("external", help="train on one repetition CSV, test on another (binary, nothing tuned on test)")
    ex.add_argument("--full-features", action="store_true", help="also evaluate the complete feature set (needs MediaPipe on both sides)")
    ex.add_argument("--json", type=Path, default=None, help="also write aggregate results as JSON (used by the research page)")
    ex.add_argument("--title", type=str, default=None)
    ex.add_argument("--train", type=Path, required=True)
    ex.add_argument("--test", type=Path, required=True)
    ex.add_argument("--report", type=Path, required=True)
    ex.add_argument("--seed", type=int, default=0)
    lo = sub.add_parser("lopo", help="leave-one-participant-out evaluation on a repetition CSV")
    lo.add_argument("--data", type=Path, required=True)
    lo.add_argument("--seed", type=int, default=0)
    lo.add_argument("--report", type=Path, default=None)
    lo.add_argument("--json", type=Path, default=None, help="also write aggregate results as JSON (used by the research page)")
    pf = sub.add_parser("perf", help="measure backend analysis cost and WebSocket round trip on this computer")
    pf.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()

    if a.cmd == "perf":
        from app.ml.perf import run_perf

        res = run_perf()
        print(json.dumps(res, indent=2))
        if a.json:
            a.json.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return
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
    elif a.cmd == "fetch-rehab24-videos":
        from concurrent.futures import ThreadPoolExecutor

        from app.ml.rehab24 import ZENODO_VIDEOS_URL, needed_recordings, video_entry_name
        from app.ml.remote_zip import fetch_entry, list_entries

        entries = list_entries(ZENODO_VIDEOS_URL)
        jobs = []
        for (exd, video, cam) in sorted(needed_recordings(a.root)):
            name = video_entry_name(entries, exd, video, cam)
            if name:
                jobs.append((name, a.root / "videos" / name))
        print(f"{len(jobs)} videos to fetch")

        def one(job):
            name, dest = job
            n = fetch_entry(ZENODO_VIDEOS_URL, name, dest)
            print(f"  {name}: {'already present' if n == 0 else f'{n / 1e6:.0f} MB'}", flush=True)

        with ThreadPoolExecutor(a.workers) as pool:
            list(pool.map(one, jobs))
        print("done")
    elif a.cmd == "extract-rehab24-videos":
        import time

        import numpy as np

        from app.ml.rehab24 import needed_recordings, video_entry_name
        from app.ml.video_pose import MediaPipeDetector, extract_ranges

        need = sorted(needed_recordings(a.root).items())
        if a.limit:
            need = need[:a.limit]
        out_dir = a.root / "mediapipe"
        for k, ((exd, video, cam), ranges) in enumerate(need, 1):
            base = out_dir / f"Ex{exd}" / f"{video}-c{cam}"
            if base.with_name(base.name + "_meta.json").exists():
                print(f"[{k}/{len(need)}] {video} cam{cam}: already extracted", flush=True)
                continue
            videos = list((a.root / "videos" / f"Ex{exd}").glob(f"{video}-Camera{cam}-30fps*.mp4"))
            if not videos:
                print(f"[{k}/{len(need)}] {video} cam{cam}: video missing, skipped", flush=True)
                continue
            t0 = time.time()
            a2d, a3d, meta = extract_ranges(videos[0], ranges, lambda: MediaPipeDetector(a.model))
            base.parent.mkdir(parents=True, exist_ok=True)
            np.save(base.with_name(base.name + "_2d.npy"), a2d)
            np.save(base.with_name(base.name + "_3d.npy"), a3d)
            meta.update({"video_file": videos[0].name, "model": a.model.name, "seconds": round(time.time() - t0, 1)})
            base.with_name(base.name + "_meta.json").write_text(json.dumps(meta), encoding="utf-8")
            print(f"[{k}/{len(need)}] {video} cam{cam}: {meta['detected']}/{meta['processed']} frames with a person, "
                  f"{meta['width']}x{meta['height']}, {meta['seconds']}s", flush=True)
    elif a.cmd == "import-own":
        from app.ml.own_recordings import import_recordings

        rows, stats = import_recordings(a.dir, include_synthetic=a.include_synthetic)
        for msg in stats.pop("problem_messages", []):  # type: ignore[arg-type]
            print("  rejected:", msg)
        if rows:
            out = a.out or a.dir / "reps.csv"
            write_csv(rows, out)
            print(f"Wrote {len(rows)} repetitions to {out}")
        print(json.dumps(stats))
    elif a.cmd == "count-eval":
        from app.ml.count_eval import blocks_rehab24_mocap, blocks_rehab26, evaluate_blocks

        out = {}
        for name, loader, root in (("REHAB26 (MediaPipe skeletons)", blocks_rehab26, a.rehab26),
                                   ("REHAB24-6 (motion-capture joints)", blocks_rehab24_mocap, a.rehab24)):
            blocks = loader(root)
            out[name] = evaluate_blocks(blocks)
            for mode, m in out[name].items():
                print(f"{name:34s} {mode:13s} blocks={m['blocks']:3d} labelled={m['labelled_repetitions']:4d} detected={m['detected_repetitions']:4d} "
                      f"MAE count={m['mean_absolute_count_error']:.2f} exact={m['exact_count_fraction']:.2f} F1={m['f1']:.2f}")
        _write_result(a.json, "counting", "Repetition counting vs labelled repetition boundaries",
                      "Real recordings; 'illustrative' uses the exercise definition's angles, 'auto' calibrates the range from the "
                      "recording itself (no labels). Healthy volunteers, a few people, 2D single-view angles. Preliminary.", out)
    elif a.cmd == "angle-eval":
        from app.ml.angle_eval import evaluate_rehab24

        ev = evaluate_rehab24(a.root)
        o = ev["overall"]
        print(f"recordings={ev['recordings']} (skipped {ev['recordings_skipped']}) n={o['n']} MAE={o['mae_deg']:.2f} deg "
              f"RMSE={o['rmse_deg']:.2f} bias={o['bias_deg']:.2f} r={o['pearson_r']:.3f} best_lag_median={ev['best_lag_frames_median']}")
        for k, m in {**ev["by_exercise"], **ev["by_camera"]}.items():
            print(f"  {k:20s} n={m['n']:6d} MAE={m['mae_deg']:.2f} RMSE={m['rmse_deg']:.2f} bias={m['bias_deg']:.2f}")
        _write_result(a.json, "angle", "Joint-angle accuracy: MediaPipe vs motion capture (REHAB24-6)", ev["note"], ev)
    elif a.cmd == "import-rehab24-video":
        from app.ml.rehab24 import import_rehab24_video

        rows, stats = import_rehab24_video(a.root)
        out = a.out or a.root / "reps_video.csv"
        write_csv(rows, out)
        print(f"Wrote {len(rows)} repetitions to {out}\n{json.dumps(stats)}")
    elif a.cmd == "external":
        tr, te = read_csv(a.train), read_csv(a.test)
        ev = external_validation(tr, te, seed=a.seed, full_features=a.full_features)
        a.report.write_text(render_external_report(ev, str(tr[0]["source"]), str(te[0]["source"])), encoding="utf-8")
        print(f"Report: {a.report}")
        _write_result(a.json, "external", a.title or f"External validation: {tr[0]['source']} -> {te[0]['source']}",
                      "Binary correct-vs-incorrect, nothing tuned on the test dataset, few participants, wide intervals. "
                      "Preliminary and non-clinical.", ev)
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
        _write_result(a.json, "lopo", f"Leave-one-participant-out evaluation on {rows[0]['source']}",
                      "Healthy volunteers performing deliberate errors, single camera views, 5 participants. Tuned methods choose "
                      "settings on training participants only. Preliminary and non-clinical.", ev)
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
        rows_src = sorted({str(r["source"]) for r in read_csv(a.data)})
        _write_result(a.json, "synthetic" if rows_src == ["synthetic"] else "train",
                      "Pipeline check on SYNTHETIC data" if rows_src == ["synthetic"] else f"Train/test on {', '.join(rows_src)}",
                      "SYNTHETIC DATA ONLY: labels come from a generator that mirrors the rule thresholds. Shows the pipeline runs; "
                      "says nothing about accuracy on real people." if rows_src == ["synthetic"] else "Preliminary.", ev)


if __name__ == "__main__":
    main()
