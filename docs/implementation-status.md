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
- [ ] Next for research: richer posture features (torso tilt, shoulder elevation, symmetry, depth cues), per-exercise tuned targets using training participants only, shoulder extension exercise, second dataset (REHAB24-6), repetition-count evaluation against Segmentation.csv
- [ ] Raw data is git-ignored (licence); generated reps.csv/lopo_report.md live in datasets/external/rehab26/

## Later phases: not started
Pose estimation, angles, repetition counter, assessment, ML, adaptation, dashboard, AR, 3D, evaluation.




