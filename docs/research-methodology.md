# Research methodology

Everything below states what is **implemented and measured**, and separates it from what is **proposed**. No result is invented; every number comes from a script in this repository (`docs/results/*.json`, shown on the app's Research page).

## 1. Problem and motivation
Home rehabilitation depends on doing exercises correctly and at a suitable difficulty, but patients rarely have an expert watching. Commodity webcams plus human pose estimation could give feedback and adapt difficulty, yet (a) single-camera angles are noisy and view-dependent, (b) movement-quality classifiers are rarely evaluated on people they were not trained on, and (c) automatic difficulty changes can be unsafe if based on unreliable measurements.

## 2. Objectives
1. Build an end-to-end, local, camera-only framework: pose estimation, joint angles, repetition counting, quality assessment, feedback, adaptive difficulty, session logging.
2. Evaluate each stage honestly on real recordings, with participant-level splits and external validation.
3. Design a conservative adaptive controller whose safety properties can be tested without patients.

## 3. Research questions and what was found
| RQ | Method | Finding (preliminary, non-clinical) |
|---|---|---|
| RQ1 How accurate are webcam-derived 2D joint angles? | MediaPipe vs optical motion capture on the same frames (REHAB24-6), MAE/RMSE/bias/limits of agreement | MAE 8.0°, RMSE 14.2°, bias -2.1°, r = 0.97 over 49,171 frames; larger for shoulder abduction (8.9°) than squat (6.8°); depends on camera |
| RQ2 Can repetitions be counted reliably? | counter vs labelled repetition boundaries, 2 datasets; illustrative vs self-calibrated range | REHAB26: F1 0.90 and count error 1.0 (illustrative) -> F1 0.97 and 0.2 (calibrated from the recording, no labels) |
| RQ3 Can movement quality be classified from joint angles alone? | rule-based and Random Forest, leave-one-participant-out, REHAB26 (5 people) | near chance: balanced accuracy 0.48-0.53 across the rule-based and angle-only methods |
| RQ4 Do posture and depth features help, and does it generalise? | ablation + nested tuning; external test train REHAB26 -> test REHAB24-6 videos, MediaPipe on both | yes, modestly: 0.49 (angle only) -> 0.61 (full features) -> 0.69 with a decision threshold chosen on training data only; weaker for arm abduction |
| RQ5 Does the skeleton source limit transfer? | same external test with motion-capture skeletons vs MediaPipe | no: 0.61 with either, so the gap to in-domain (0.72) reflects people/setup shift |
| RQ6 Is the adaptive controller safe and stable? | unit tests, property tests over long random histories, mutation check, simulation vs fixed levels | bounds and "never up on unreliable data" hold; fewer badly matched sessions than the best fixed level under stated assumptions; a bounded amount of reversal for users near a boundary. **No claim about recovery** |

## 4. System and methods (implemented)
- **Pose estimation**: MediaPipe Pose Landmarker (lite, in the browser; Full on videos for evaluation) behind a replaceable interface; a synthetic estimator for demos and tests.
- **Angles**: 2D three-point angle with confidence gating, isotropic coordinate correction, exponential smoothing that skips gaps and rejects one-off spikes but accepts persistent jumps.
- **Repetition counter**: state machine (rest, moving out, target, returning) on progress normalised between a start and target angle, with hysteresis, minimum duration, and gap abort.
- **Features**: per repetition: range, duration, speed, extra direction reversals, reliability; posture features from landmarks (torso tilt, shoulder elevation asymmetry, head tilt, elbow bend, left-right asymmetry, knee valgus, heel lift, knee-over-toe) and MediaPipe 3D depth cues.
- **Assessment**: configurable rule-based baseline (`insufficient_data` when unreliable); Random Forest as the ML baseline.
- **Adaptive controller**: see `docs/adaptive-controller.md`.

## 5. Data
| Dataset | Use | Notes |
|---|---|---|
| REHAB26-ViewAngles (Zenodo 23018128, CC BY-NC 4.0) | training and leave-one-participant-out | 5 healthy volunteers, 3 exercises, 1,665 labelled repetitions, MediaPipe skeletons |
| REHAB24-6 (Zenodo 13305826, CC BY-NC 4.0) | external validation; angle accuracy; counting | 10 volunteers, mocap skeletons and videos; binary labels; MediaPipe re-run on the videos |
| Synthetic generator | software tests and pipeline checks only | labels come from the generator: never evidence of accuracy |
| Own recordings (optional tool) | closest-to-deployment validation | `docs/user-guide.md`; take-level labels |
Details, licences and limits: `docs/dataset-documentation.md`. Raw data is not redistributed.

## 6. Evaluation design
- **No leakage**: all splits are by participant; tests assert no participant appears on both sides; leave-one-participant-out for the small dataset.
- **No test-set tuning**: forest settings, range-rule thresholds and the ML decision threshold are chosen only from training participants (nested); tests assert the test labels never influence them.
- **Uncertainty**: 95% intervals by bootstrapping whole participants; sample sizes reported. With 5 to 10 people, intervals are wide and no significance test is meaningful.
- **Baselines**: majority class, untuned and tuned rule-based, angle-only forest, so each addition is measured against a simpler alternative.
- **External validity**: train on one dataset, test on another with different people, cameras and setting; plus an in-domain reference to separate "hard task" from "shifted data".
- **Calibration**: Brier score and expected calibration error of the predicted probability; the probabilities are over-confident and are not shown to users.
- **Simulation**: explicitly labelled; verifies controller behaviour under stated assumptions only.

## 7. Reproducibility
`docs/installation.md` lists every command; evaluation scripts write JSON to `docs/results/` and Markdown reports; seeds are fixed; model artifacts are versioned with the data hash. Automated tests need no data or camera.

## 8. Research contribution statement
Pose estimation, machine learning, and 3D/AR interfaces are each established; none is claimed as novel here. What this project contributes is:
1. **A conservative, explainable adaptive-difficulty policy gated on measurement reliability** (never raising difficulty on unreliable or scarce data, multi-session confirmation, a dead zone, one-step changes, a pause rule, explicit reset) with its safety properties **verified by automated and property-based tests and a behaviour simulation**, designed to run from camera-only data.
2. **An honest, reproducible evaluation methodology for webcam movement-quality assessment**: participant-level splits, nested tuning with leakage tests, external validation including a like-for-like pipeline on a second dataset, and a decomposition showing that skeleton source was not the limiting factor.
3. **Empirical findings of practical value**: joint angle alone is near chance for quality classification on unseen people; posture and depth features give a real but modest gain; a decision threshold chosen on training data transfers while default probabilities do not; calibrating the counting range from the recording itself markedly improves counting.
4. **An open tool chain** for repeating this on a lab's own recordings (record-data page, importers, evaluation scripts).
What it does **not** show: that any of this improves recovery, or that it is clinically valid.

## 9. Threats to validity
Few, healthy, scripted participants; deliberate rather than natural errors; take-level labels in own recordings; 2D single-view angles; illustrative thresholds; simulation outcomes follow from assumed user models; mocap is a reference with definitional differences; model and label choices were made by the author without clinical input.

## 10. Future work (proposed, not implemented)
Live per-user range calibration; clinician-defined error taxonomy and labels; a study on the target population with ethics approval; a temporal model (LSTM/GRU/transformer) on landmark sequences; better-calibrated probabilities (for example isotonic calibration on a validation set); multi-view or depth cameras; AR camera-overlay mode and a 3D/VR environment; evaluation of adaptive versus fixed difficulty in a randomised trial.

## 11. References
Cite from primary sources before use: the dataset records and papers named on their Zenodo pages (REHAB26-ViewAngles; REHAB24-6, Cernek, Sedmidubsky and Budikova, SISAP 2024), the MediaPipe Pose documentation, scikit-learn, and the public rehabilitation datasets surveyed (UI-PRMD, KIMORE, IntelliRehabDS). A literature-review outline is in `docs/thesis-outline.md`. No citation is reproduced here from memory.
