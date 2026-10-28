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
- [x] Results, 5 participants, LOPO: binary balanced accuracy RF angle-only 0.53 (tuned 0.54) -> RF + posture 0.61 (tuned 0.63); 3-class macro-F1 0.43 (0.42 tuned) -> 0.59 (0.57 tuned), CIs 0.30-0.50 vs 0.49-0.65 (wide, n=5). Tuned single range rule: macro-F1 0.37; untuned rule 0.10; majority 0.22. Per-participant: tuned posture model better than tuned angle-only for 4 of 5 held-out people (worse for one of them). Participants are pseudonymised on import (R26-P1 ... R26-P5).
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

## Phase 6 - Frontend pages and dashboard (done; verified in the browser at desktop and phone width)
- [x] Routed app (react-router): Landing, Exercise library (illustrative range diagrams, level tables), Live session (camera / synthetic demo, adaptive level, recommendation card), Session summary (/sessions/:id: metrics, chart, every repetition, the suggestion and its reasons), Dashboard, Research evaluation, Settings & privacy, Sign in / create account, 404. Shared layout with skip link, persistent safety banner, backend-down banner, keyboard focus styles, light/dark themes, responsive down to phone width (no horizontal page scroll on any page at 375 px); chart and camera pages are lazy-loaded.
- [x] Dashboard (signed-in): totals, average score, time exercising, charts (score + flagged share, difficulty played vs suggested, movement range, repetitions vs target, issue categories), filters (exercise, date range, include-demo which is off by default and visibly labelled), session table linking to details, CSV export of sessions and repetitions. Empty, loading and error states. All labelled as experimental system metrics.
- [x] Research page: renders the aggregate JSON written by the evaluation scripts (`--json`), including CI whiskers; synthetic results carry a prominent warning. Raw datasets are never exposed (a test asserts the JSON has no per-person rows).
- [x] Settings & privacy: plain-language privacy notice, profile and spoken-feedback default, CSV download, per-exercise adaptive reset, delete account and data.
- [x] Backend additions: GET /api/sessions/{id}/detail, /api/analytics/export.csv, date filters (`from`/`to`), duration and mean range per session, GET /api/research/results. Fixed: the pause reason no longer says "very low quality" when the trigger was a 100% flagged share with a moderate score.
- [x] Tests: backend suite passes (see below). No frontend unit tests yet; frontend behaviour was checked by hand in the browser.
- [ ] Not built: separate "pose visualization and movement analysis" page (the skeleton, live angles and per-repetition analysis live inside the Live session page), AR mode and 3D room (Phase 7), live-camera dashboard check on real camera sessions, automated browser tests, per-user charts of ML predictions (the ML classifier is not used in the live loop).

## Phase 6b - Limitation fixes (everything that could be fixed in code or by measurement)
- [x] **Repetition counting evaluated** against the datasets' labelled boundaries (backend/app/ml/count_eval.py; a bug found and fixed on the way: detected intervals were offset twice, caught by comparing counts with F1). REHAB26: F1 0.90 / mean count error 1.02 with illustrative angles; F1 0.97 / 0.20 when the range is calibrated from the recording itself (no labels). REHAB24-6 mocap: F1 0.89 either way.
- [x] **Angle accuracy (MAE/RMSE) vs motion capture** (backend/app/ml/angle_eval.py): 49,171 frames, 31 recordings: MAE 8.02 deg, RMSE 14.24 deg, bias -2.14 deg, r = 0.970, frames aligned (median best lag 0); by exercise and camera in docs/results/angle-accuracy.json.
- [x] **Probability calibration and threshold selection**: the decision threshold is chosen from training participants only (out-of-fold), tested to never see test labels. External test (like-for-like MediaPipe): balanced accuracy 0.614 -> 0.686 (95% CI 0.625-0.761), recall 0.66, precision 0.61 (base rate 0.40). Raw probabilities remain over-confident (ECE ~0.29-0.33): reported, not shown to users.
- [x] **Adaptive vs fixed difficulty**: SIMULATION (backend/app/personalization/simulation.py), clearly labelled; adaptive had fewer badly matched sessions than the best fixed level in all four user models (e.g. stable 0.20 vs 0.47, improving 0.11 vs 0.47, declining 0.38 vs 0.41), 0 safety violations; measured behaviour: ~1 direction reversal per 40 sessions for stable users near a level boundary (documented, bounded).
- [x] **Pose visualisation and movement-analysis page** (/analysis): skeleton, per-landmark confidence, live joint-angle trace, FPS, model time, detection rate, camera permission state. Doubles as a camera set-up check.
- [x] **Frontend tests**: 30 tests (vitest + Testing Library): angle maths and isotropic correction, demo generator, API client (token storage failure, error parsing, 204, query building), recommendation card, account panel, layout banners, dashboard (guest / empty / data / error), research page, recording validation and serialisation.
- [x] **Own-recording workflow** (so the missing "own webcam" data can be collected): /collect page (consent first, participant code not a name, landmark numbers only, nothing uploaded) + `python -m app.ml.cli import-own` (validation, constant-rate resampling without inventing data across gaps, auto-calibrated segmentation, take-level labels). 14 backend tests. NOT used yet: no recordings of your own exist.
- [x] **Documentation set**: architecture, installation (+ scripts/setup.ps1, verified), user guide (+ manual webcam test protocol), research methodology (+ contribution statement), API reference, limitations and safety, thesis outline.
- [x] Research page now renders counting, angle accuracy, simulation, and threshold/calibration results.
- [x] Tests at that point: 171 backend + 36 frontend + 15 Unity edit-mode (see the end of this file for the current counts).

### Limitations that remain (cannot be fixed by code alone)
- [ ] The **live webcam path has not been run on a real webcam** by the author: manual protocol in docs/user-guide.md is for you to run.
- [ ] **Clinical review** of exercise ranges, error definitions and controller thresholds; **real patient data**; any claim of benefit needs a study with ethics approval.
- [ ] **Live range calibration** (the counting evaluation shows it would help) is a recommended product change, not built.
- [ ] **ML is not used in the live loop** (by design; see limitations doc). A temporal model (LSTM/GRU) was not built.
- [ ] **AR camera-overlay mode, desktop 3D room, immersive VR/WebXR, Unity client** (Phases 7-8): not built; no headset.
- [ ] Automated browser end-to-end tests (Playwright) are not set up; the real-camera path is manual.
- [x] Failed sign-ins are rate-limited (tested). Still no HTTPS or general API rate limiting (local prototype).

## Phase 7 - 3D room, AR camera overlay, Unity scaffold
- [x] **Desktop 3D room** (/room, Three.js via react-three-fiber, no headset): room, a virtual trainer (amber) looping the exercise's illustrative movement beside an avatar (teal) that mirrors the user; live repetitions, phase, last-repetition result, level, feedback and the same adaptive recommendation card; saves sessions like the live page. A scene error boundary keeps counting and feedback working if WebGL fails. Verified in the browser with the synthetic demo (WebGL on, avatars visible, repetitions counted). Shared `useExerciseStream` hook; 3 new tests for the trainer pose (33 frontend tests pass).
- [x] **AR camera-overlay mode** (/ar): guidance drawn over the camera picture (skeleton, dashed target ray and arc at the exercise joint, live angle, repetitions, feedback). Clearly labelled a **camera overlay, not immersive AR**; WebXR support is only detected and reported. Verified drawing with the synthetic demo; **not tested on a real camera or phone**.
- [x] **Unity client scaffold** (unity-client/): Unity 6 (6000.6.7f1) project files and C# scripts (backend WebSocket client, REST client, 3D room with trainer avatar, HUD) using the same backend. Unity Hub and Editor 6000.6.7f1 installed; licence active (Personal). **Compiles with no errors** (batch mode) and a RehabRoom scene is generated by an editor menu script. **Play mode was run by the user in the Editor (synthetic demo against the live backend): repetitions counted, feedback and suggestion shown, backend-off message shown.** Manual slider, real pose input and headsets untested; checklist in unity-client/README.md. No pose estimation in Unity (future work).
- [ ] Not built: immersive WebXR AR/VR sessions, a headset test, live per-user calibration, Unity avatars for other exercises.

## Phase 7b - Live range calibration
- [x] **Per-user range calibration** (backend/app/repetition_detection/calibration.py, services/analysis.py): the counting range is measured from the user's own first seconds of movement (10th to 90th percentile of the smoothed angle, after at least 5 s and 30 valid samples and 15 degrees of movement) and repetitions done during calibration are replayed through the counter, so none are lost. A person who does not move is never given a made-up range. WebSocket option calibrate=auto; new calibrated message; on by default in the live session (checkbox), the 3D room and the AR page. The counting evaluation motivated it (F1 0.90 -> 0.97 on REHAB26). 8 new backend tests; checked in the browser (calibrated 154 to 52 degrees on the demo).
- [x] Caveat documented: calibration describes the range the user demonstrated, NOT a clinical target; level range fractions now apply to the user's own range. Not yet evaluated end to end on real live sessions.

## Phase 7c - Unity client completed (desktop, no headset) and browser relay
- [x] **Unity client** (unity-client/, Unity 6000.6.7f1, licence active): all exercises from `GET /api/exercises`, virtual trainer + user figure built from landmarks, three angle sources (synthetic trainer demo, manual slider, live pose from the browser), live calibration option, HUD with repetitions/phase/feedback/adaptive suggestion, graceful behaviour when the backend is down. Code split into assemblies (Arvr.Runtime, Arvr.Editor, edit-mode tests).
- [x] **Verified headlessly**: compiles with no errors; **14 Unity edit-mode tests pass** (pose maths, trainer poses for 4 joint types on both sides, message/URL/relay-frame parsing, exercise-list parsing); batch build script `ARVR > Build Windows player` produced a Windows player (ARVR-Unity.exe, git-ignored) that ran headless for 12 s without crashing (its only log error was the expected backend-unreachable message).
- [x] **Verified by the user in the Editor (earlier version of the room, 2026-10-28)**: Play mode, counting, suggestion, backend-off message. The newer features (exercise picker, live-from-browser, calibration toggle) have NOT been tried by hand in Play mode.
- [x] **Local pose relay** (backend/app/api/relay.py, `WS /api/ws/relay/{room}`) + "Share live pose" panel in the web 3D room: the browser publishes landmark NUMBERS (no video/images) to a room code; Unity subscribes. In-memory only, validated frames (size, 33 finite landmarks), room/subscriber/publisher limits, 11 backend tests, 3 frontend tests. Single-user local use only; do not expose to the internet.
- [x] **VR prepared, not tested**: OpenXR packages (xr.management 4.6.1, xr.openxr 1.19.0) installed, HUD reports XR status; project still compiles and **15 Unity tests pass**. XR is off by default; a head-tracked rig and controller UI are not built.
- [ ] Not done: tested immersive VR (no headset), pose estimation inside Unity, Unity accounts/charts.

## Phase 8 - Optional immersive VR (built; NOT tested on a headset)
- [x] **Web**: the 3D room has an **Enter VR** button (native WebXR `immersive-vr`, local-floor space) shown only when the browser reports support; the room is placed 2.5 m in front of a standing user and a floating panel shows repetitions, phase and feedback. Pure parts tested (support detection incl. errors, placement, panel text); the 3D page still renders and counts with no headset (checked in the browser, no console errors).
- [x] **Unity**: OpenXR packages and an XR status line (Phase 7c). No head-tracked rig or controller UI.
- [ ] **Never run on a headset.** Treat VR as unverified. If you do not get a headset, the camera-overlay AR page (Phase 7) is the supported experience: browsers cannot give WebXR sessions the camera frames pose estimation needs, so immersive headset AR with body tracking is not feasible from the web.

## AR upgrades (camera-overlay AR is the primary experience)
- [x] Ghost trainer (translucent figure fitted to your torso), joint dots (green reached / amber moving / red unclear), setup hints (step back / closer / middle / face the camera), repetition progress bar, large per-repetition flash ("Good / Slower / Go further"), voice cues (also in the 3D room), front/back camera choice (back camera not mirrored), full-screen button. Pure logic unit-tested (`pose/guidance.test.ts`, 15 tests); drawing verified in the browser with the synthetic demo (ghost, dots, hint, progress bar, calibration, counter). **Not verified with a real camera or a phone.**

## Phase 9 - Evaluation and documentation (done as far as the data allows)
- [x] Results summary for the thesis: `docs/results/SUMMARY.md`; methodology, model card, dataset documentation, limitations and safety, thesis outline, API, architecture, install and user guide are current.
- [ ] Not possible without people: a study with participants or patients, clinician review of thresholds, a held-out test on your own webcam data (the recording tool exists).

## Extras added after the phases (all tested)
- [x] **Pain check-in** (0-10 + note, stored per session; no level raise at 4+, pause at 7+; re-evaluates the suggestion; `POST /sessions/{id}/checkin`): 10 backend tests, 2 frontend tests.
- [x] **Accessibility**: larger text and high-contrast theme (remembered in the browser), keyboard-usable controls; 3 tests.
- [x] **Backup and restore** (JSON, ownership-safe, idempotent) and a **weekly activity summary** on the dashboard: 5 backend tests, 3 frontend tests.
- [x] **Printable session report** (print stylesheet, "Print or save as PDF"), pain and note shown on the summary.
- [x] **Three more exercises** (hip abduction, hip flexion, seated knee extension; 9 in total) and a synthetic demo that can play any exercise; 10 backend tests. The synthetic training dataset is pinned to the original six exercises so earlier results stay reproducible. New exercise ranges are placeholders, checked only with synthetic movements.
- [x] **General API rate limiting** (300/min per address) and **Docker files** (`docker-compose.yml`; written, **not built or run**: the Docker engine was not running).
- [x] Tests now: 199 backend + 66 frontend + 15 Unity edit-mode (280); the frontend builds.

## Still not done
Tested immersive VR (no headset), real-camera/phone verification of the AR page, hands-on Unity Play-mode check of the newer features, clinician review, any study with people, HTTPS, Playwright end-to-end tests, LSTM/GRU baseline, Docker build.
