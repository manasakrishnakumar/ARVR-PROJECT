# Implementation status

## Phase 1 — Environment and architecture
- [x] Environment inspected: Python 3.10.11, Git 2.55, Docker present; Node.js 24.22.1 / npm 11.19.1 installed via winget during this session; Unity not found.
- [x] Repo structure (backend, docs, scripts, datasets, artifacts)
- [x] FastAPI app, config, SQLite schema (users, sessions, repetitions)
- [x] Exercise library as JSON (5 exercises, illustrative targets)
- [x] Endpoints: GET /api/health, /api/exercises, /api/exercises/{id}, POST/GET /api/sessions, GET /api/sessions/{id}
- [x] 3 API tests pass (pytest)
- [ ] Frontend (Vite+React+TS) — blocked: Node.js not installed
- [ ] docs/architecture.md, installation.md (README covers backend only so far)

## Phase 3 - Exercise analysis (done, synthetic-data tests only)
- [x] Repetition counter state machine (rest/moving_out/target/returning, hysteresis, min duration, gap abort)
- [x] Per-repetition features, rule-based assessment (acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data)
- [x] POST /api/assessment/evaluate (angle series in, repetitions and assessments out)
- [x] 22 backend tests pass; fixed AngleSmoother permanently rejecting persistent jumps
- [x] Live wiring: WebSocket /api/ws/analysis (StreamAnalyzer) <-> Pose lab session UI: exercise + manual difficulty select, rep counter vs target, phase chip, progress bar, once-per-rep feedback, optional audio, rep table, pose-lost warning. 25 backend tests pass; verified in browser with synthetic demo (3/5 reps counted, all 'acceptable').
- [ ] Real webcam path and non-elbow exercises NOT yet tested live (demo only animates elbow flexion); thresholds illustrative; no real human recordings yet
- [ ] Sessions are not persisted yet (Phase 5/6); difficulty is manual until the adaptive controller exists

## Phase 4 - Machine learning (pipeline done; SYNTHETIC data only)
- [x] Dataset schema + validation + CSV I/O, participant-level split (leakage test), synthetic generator (labelled synthetic)
- [x] Random Forest training, versioned model + metadata, inference with explicit 'uncertain' state, GET /api/models/status
- [x] Evaluation vs majority-class and rule-based baselines: accuracy, per-class P/R/F1, confusion matrix, participant-bootstrap CI; report at artifacts/reports/<version>/report.md
- [x] 36 backend tests pass; run with scripts\train_model.ps1
- [ ] No real data yet: results on synthetic data show the pipeline works, NOT that ML beats rules on real people (generator mirrors rule thresholds). ML is preliminary.
- [ ] ML not yet used in the live session / evaluate endpoint; Kaggle dataset not chosen (needs user account + label-mapping check)
- [ ] LSTM/GRU, angle MAE/RMSE, repetition-count evaluation: not started

## Phase 4b - Real data: REHAB26-ViewAngles (Zenodo, CC BY-NC 4.0) - first real-data results
- [x] Downloaded (with user consent) labels + MediaPipe skeleton zip; verified zip contents (only .npy), array shapes, and label counts match the documentation
- [x] Importer (backend/app/ml/rehab26.py), leave-one-participant-out evaluation (ml/lopo.py), CLI: import-rehab26, lopo; 41 backend tests pass
- [x] Result (5 participants, 1084 reps, 3 classes acceptable/insufficient_range/posture_deviation): binary correct-vs-incorrect balanced accuracy RF 0.523, rule-based 0.496, majority 0.500; 3-class macro-F1 RF 0.427 (CI 0.338-0.518), rule 0.095, majority 0.222. Per-participant RF accuracy 0.34-0.61.
- [x] INTERPRETATION: with one joint angle plus the untuned illustrative thresholds, real-data quality detection is near chance. Posture errors (433 of 1084 reps) are largely invisible to these features, and even the range class is poorly detected. This is a negative result to report honestly, not a defect hidden by tuning.
- [x] Posture features added (feature_extraction/posture.py, 14 features: torso tilt, shoulder elevation asymmetry, head tilt, elbow bend 2D/3D, left-right asymmetry, 3D range and depth cue, knee valgus, heel lift, knee-over-toe) + ablation + nested tuning (hyperparameters and a range-rule threshold chosen on training participants only; leakage test). 47 tests pass. Full table: docs/results/rehab26-lopo-report.md
- [x] Results, 5 participants, LOPO: binary balanced accuracy RF angle-only 0.53 (tuned 0.54) -> RF + posture 0.61 (tuned 0.63); 3-class macro-F1 0.43 (0.42 tuned) -> 0.59 (0.57 tuned), CIs 0.30-0.50 vs 0.49-0.65 (wide, n=5). Tuned single range rule: macro-F1 0.37; untuned rule 0.10; majority 0.22. Per-participant: tuned posture model better than tuned angle-only for 4 of 5 held-out people (worse for R26-P5).
- [x] Honest reading: posture features give a real but modest gain; correct-vs-incorrect is ~63% balanced accuracy, far from deployment quality. Nested hyperparameter tuning gave no clear benefit. Many acceptable reps are flagged posture_deviation (222 of 543). Feature importance is descriptive, not causal. No significance test is meaningful with n=5.
- [ ] Still open: shoulder extension, second dataset (REHAB24-6) for external validation, repetition-count evaluation against Segmentation.csv, validation on own webcam recordings, class definitions reviewed by a rehabilitation professional
- [ ] Raw data is git-ignored (licence); generated reps.csv/lopo_report.md live in datasets/external/rehab26/

## Later phases: not started
Pose estimation, angles, repetition counter, assessment, ML, adaptation, dashboard, AR, 3D, evaluation.





