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
## Phase 4c - Shoulder extension + external validation on REHAB24-6
- [x] Shoulder extension exercise definition (illustrative targets) + importer support; camera selection now uses landmark visibility (no labels); video aspect (9:16, inferred) correction applied in the importer AND the live page (isotropic()); 56 tests pass
- [x] REHAB26 LOPO re-run on all 1,665 reps (3 exercises, 5 people), aspect-corrected: rf_posture_tuned binary balanced acc 0.676, 3-class macro-F1 0.627 (CI 0.57-0.68); angle-only tuned 0.499 / 0.310; untuned rule 0.483 / 0.112. Uncorrected-aspect sensitivity: posture results essentially unchanged (0.685 / 0.602), so the conclusions do not hinge on the 9:16 assumption.
- [x] REHAB24-6 downloaded (2d_joints, 693 MB, verified) and imported (369 reps, arm abduction + squat, 9 people with usable reps, mocap skeletons)
- [x] EXTERNAL VALIDATION (train on REHAB26 only, nothing tuned on test, binary): rf angle+posture balanced acc 0.608 (95% CI 0.561-0.656), angle-only 0.532, tuned range rule 0.528, majority 0.500; in-domain reference on REHAB24-6 itself 0.689. By exercise: squat 0.664, arm abduction 0.522 (no transfer). Docs: docs/results/external-validation-rehab26-to-rehab24.md
- [x] Honest reading: the posture-feature gain over angle-only replicates on an independent dataset, but it is small (about 0.61 balanced accuracy) and does not transfer for arm abduction. On the new data the model flags almost everything as incorrect (recall 0.98, precision 0.47 vs base rate 0.40): the decision threshold does not transfer, and the skeleton-source difference (mocap vs MediaPipe) confounds the drop. Not usable as a classifier yet.
- [ ] Still open: repetition-count evaluation against Segmentation.csv, own webcam recordings (same pipeline, MediaPipe), run MediaPipe on REHAB24-6 videos for a like-for-like external test, probability calibration / threshold selection, class definitions reviewed by a rehabilitation professional
- [ ] Raw data is git-ignored (licence); generated reps.csv/lopo_report.md live in datasets/external/rehab26/

## Phase 4d - Like-for-like external validation: MediaPipe on the REHAB24-6 videos
- [x] Fetched only the needed 31 videos (668 MB of a 2.65 GB zip) via HTTP range requests (backend/app/ml/remote_zip.py, with retry on transient errors; tested against a local range server), ran MediaPipe Pose **Full** (the family REHAB26 used) on the labelled repetition frames only (backend/app/ml/video_pose.py, ~36 fps CPU, a person found in every processed frame in the first recording). Visually checked a skeleton overlay on a real frame. Camera 18 files are portrait but upright (no rotation needed). Extracted arrays store the real video width/height for exact aspect correction; no video frames are stored by the project. Optional deps: backend/requirements-video.txt.
- [x] 369 repetitions (arm abduction + squat, 9 people with usable reps) imported with the same feature code as REHAB26, including head tilt, heel lift and MediaPipe 3D cues.
- [x] RESULT (train on REHAB26 only, nothing tuned on test, binary correct vs incorrect, balanced accuracy, 95% CI over participants): majority 0.500; tuned range rule 0.529 (0.48-0.59); RF angle-only 0.492 (0.42-0.56, chance); RF + common posture features 0.579 (0.53-0.63); **RF + full posture features 0.614 (0.56-0.67)**. In-domain reference inside REHAB24-6 (leave-one-participant-out): 0.64 angle-only, 0.72 full. By exercise (full features): squat 0.641, arm abduction 0.567. Report: docs/results/external-validation-like-for-like-mediapipe.md
- [x] Reading: (1) with the SAME estimator on both sides the transfer result (0.61) is about the same as the earlier mocap-skeleton test (0.61), so the skeleton-source difference was not what limited transfer; the gap to the in-domain 0.72 reflects genuine dataset/setup shift (people, camera, lighting, how errors were produced). (2) The posture-feature benefit over angle-only holds on independent data and with the full feature set, but the absolute level is low. (3) The model still labels almost everything incorrect on new data (recall 0.99, precision 0.47 vs base rate 0.40): the decision threshold does not transfer, so this is not a usable classifier. (4) Arm abduction transfers poorly. (5) 9 participants and a lenient CI: treat as preliminary.
- [ ] Still open: repetition-count evaluation against Segmentation.csv, own webcam recordings, probability calibration / threshold selection on a validation set, review of class definitions by a rehabilitation professional

## Phase 5 - Adaptive personalization, accounts, persistence (done; synthetic-data tests + one browser run)
- [x] Adaptive controller (backend/app/personalization): config file, session classification, multi-session hysteresis, safety bounds, pause, reset, explainable reasons. Independent of camera/DB. Docs: docs/adaptive-controller.md. 28 unit tests incl. long random histories and a mutation check.
- [x] Accounts and profiles: register/login/logout/me/update/delete (scrypt hashing, hashed bearer tokens, no username enumeration, validated profile + preferences); guest mode; per-session secret for the live stream.
- [x] Persistence: users, sessions, repetitions (with counted/reliable), adaptive decisions; old prototype databases upgrade in place (tested; also happened for real on the dev DB). Repetitions are saved server-side as they finish on the WebSocket.
- [x] API: POST /sessions, GET /sessions(/id), POST /sessions/{id}/repetitions, POST /sessions/{id}/complete, POST /adaptation/recommend (stateless), GET /adaptation/state, POST /adaptation/reset, GET /analytics/summary and /progress. Demo and guest sessions never feed history or analytics.
- [x] Frontend: account panel (guest / sign in / register / delete my data), suggested level, "Stop and save", recommendation card with reasons and safety note, per-user session table. Verified in the browser (register, demo session, recommendation card, account deletion; test account removed, DB empty afterwards).
- [x] 109 backend tests pass.
- [ ] NOT verified: real-camera sessions through the full adaptive loop; the adaptive thresholds on real users; any claim that adaptation helps recovery (needs a study). Increase path was verified through the API with synthetic streams, not by hand in the browser (demo sessions are deliberately excluded from history).
- [ ] Not yet built: adaptive-vs-fixed simulation report, dashboard charts (Phase 6), exportable CSV, settings page, AR/3D (Phase 7)

## Later phases: not started
Pose estimation, angles, repetition counter, assessment, ML, adaptation, dashboard, AR, 3D, evaluation.






