# Thesis draft (working text)

*An AI-Driven Adaptive AR/VR Framework for Personalized Rehabilitation Using Vision-Based Human Pose Estimation*

Status: a working draft assembled from this repository's measured results. **Chapter 2 (literature review) is deliberately not written here**: it must be built from sources you have read and verified; no citations have been invented. Every number below is traceable to `docs/results/` or to a test. Wording is cautious on purpose; keep it that way. Structure follows `docs/thesis-outline.md`.

## Abstract (draft)
Home rehabilitation depends on correct execution and suitable difficulty, but patients seldom have an expert watching. This work builds and evaluates a local, camera-only framework that estimates body pose in the browser, measures joint angles, counts repetitions, assesses movement quality, gives feedback, and suggests the next difficulty level, presented as a 2D page, a camera-overlay AR view and a 3D room. The adaptive controller is conservative and fully tested for safety properties. Using two public datasets (REHAB26-ViewAngles and REHAB24-6) we measure: joint-angle error against motion capture (mean absolute error 8.0 degrees over 49,171 frames, correlation 0.97); repetition counting (F1 0.90 with illustrative ranges, 0.97 with per-user range calibration); and movement-quality classification, which transfers only modestly between datasets (balanced accuracy 0.69 externally with the full feature set against 0.49 with angle features alone). The adaptive controller is evaluated by tests and simulation only. No patients took part; no claim about clinical benefit is made. Immersive VR was prepared but not tested on a headset.

## 1. Introduction
**Motivation.** Adherence and technique matter in home rehabilitation, and commodity webcams with pose estimation make low-cost feedback conceivable. Three practical problems stand in the way: single-camera joint angles are noisy and view dependent; quality classifiers are rarely tested on people they were not trained on; and automatic difficulty changes can be unsafe if driven by unreliable measurements.

**Objectives.** (1) Build an end-to-end local framework: pose, angles, counting, assessment, feedback, adaptation, logging. (2) Evaluate every stage on real recordings with participant-level splits and external validation. (3) Design an adaptive controller whose safety properties can be tested without patients.

**Research questions.** RQ1 accuracy of webcam 2D angles; RQ2 reliability of repetition counting; RQ3 quality classification from angles alone; RQ4 value and transfer of posture and depth features; RQ5 whether the skeleton source limits transfer; RQ6 safety and stability of the adaptive controller (`docs/research-methodology.md`).

**Scope and non-goals.** A research prototype; not a medical device; no clinical validation; no claim that adaptation improves recovery. Presentation modes: desktop page, camera-overlay AR (not immersive), desktop 3D room, and an optional Unity client; immersive VR is prepared but untested.

## 3. Requirements and system design
**Constraints**: a laptop with a webcam, CPU only, open-source components, privacy by design (video never leaves the browser; the backend receives joint-angle numbers only; local database).
**Architecture** (`docs/architecture.md`): browser pose estimation (MediaPipe Pose Landmarker, lite model, running in the page) -> joint angle with confidence gating -> WebSocket to the backend -> stream analyzer (smoothing, state-machine repetition counter with hysteresis, optional per-user range calibration) -> rule-based assessment -> session persistence -> adaptive controller -> recommendation. Presentation layers (live page, AR overlay, 3D room, Unity) share this pipeline, so counting and suggestions are identical everywhere.
**Exercise library**: nine exercises defined as data (JSON); targets are illustrative placeholders, not prescriptions.
**Safety design**: unreliable data never raises difficulty; changes are one step at a time between sessions; two confirming sessions; a dead zone; reported pain only makes the suggestion more cautious; every suggestion carries its reasons; accounts are optional and data can be exported, backed up and deleted.

## 4. Methods
**4.1 Angles.** Three-point 2D angle at the joint with an isotropic correction for non-square video, confidence gating, and exponential smoothing that skips gaps and rejects one-off spikes but accepts persistent jumps.
**4.2 Counting.** States rest, moving out, target, returning on progress normalised between a start and a target angle; hysteresis, minimum duration, gap abort. With calibration enabled the start and target come from the user's own first seconds (10th and 90th percentile after at least 5 s, 30 valid samples and 15 degrees of movement), and repetitions made during calibration are replayed so none are lost.
**4.3 Features.** Per repetition: range, duration, speed, direction reversals, reliability; posture features (torso tilt, shoulder elevation asymmetry, head tilt, elbow bend, left-right asymmetry, knee valgus, heel lift, knee over toe) and MediaPipe depth cues (14 in total).
**4.4 Assessment.** A transparent rule set labels each repetition acceptable, insufficient range, incomplete, too fast, uncontrolled or insufficient data (never guessed). A Random Forest is the machine-learning baseline.
**4.5 Adaptive controller.** Described in `docs/adaptive-controller.md`: classification of each session, increase after two good sessions, decrease after two poor sessions, pause on a very poor session or reported pain, reset on request.
**4.6 Evaluation protocol.** Participant-level splits only; leave-one-participant-out with nested tuning (tests assert the held-out person is never seen during tuning); bootstrap intervals that resample participants; external validation (train on one dataset, test on another) with the decision threshold chosen on training data only; calibration (Brier score, expected calibration error).

## 5. Implementation
Backend: Python 3.10, FastAPI, SQLAlchemy with SQLite, WebSockets, scikit-learn; scrypt password hashing, hashed bearer tokens, sign-in lockout and request rate limits. Frontend: React, TypeScript, Vite, Recharts, three.js, MediaPipe tasks-vision. Optional Unity 6 client with a local pose relay. Testing: about 280 automated tests (backend, frontend, Unity edit mode) covering angle maths, counter, assessment, controller bounds (including property tests over long random histories), API validation and ownership, persistence, importers and evaluation code. What tests cannot cover (real camera, lighting, bodies, headsets) is listed in `docs/limitations-and-safety.md` with a manual protocol.

## 6. Evaluation and results
Datasets: REHAB26-ViewAngles (Zenodo 23018128, CC BY-NC 4.0; 5 healthy volunteers, 3 exercises, 1,665 labelled repetitions) and REHAB24-6 (Zenodo 13305826, CC BY-NC 4.0; 10 volunteers, motion capture plus video). Raw data is not redistributed; participants are pseudonymised R26-P1 to R26-P5. Full table with files: `docs/results/SUMMARY.md`.

| RQ | Result | Reading |
|---|---|---|
| RQ1 angle accuracy | MAE 8.02 deg, RMSE 14.24 deg, bias -2.14 deg, r 0.97 (49,171 frames; shoulder abduction MAE 8.9 deg, squat 6.8 deg; depends on camera) | Useful for counting and coarse range; not a clinical measurement. Part of the error is definitional (motion-capture joint centres versus landmarks) |
| RQ2 counting | REHAB26 F1 0.90 -> 0.97 with per-user calibration, count error 1.0 -> 0.2 | Calibration clearly helps; it describes the range the user demonstrated, not a target |
| RQ3 angle-only quality | balanced accuracy 0.48-0.53 | near chance |
| RQ4 posture/depth features | 0.49 (angle only) -> 0.61 (all features) -> 0.686 (95% CI 0.625-0.761) with a threshold chosen on training data | a real but modest gain; weaker for arm abduction |
| RQ5 skeleton source | 0.61 with motion-capture or MediaPipe skeletons | the gap to the in-domain 0.72 reflects people and setup shift, not the skeleton source |
| Calibration of probabilities | mean predicted 0.70 against 0.40 observed | over-confident: do not show probabilities as certainty |
| RQ6 controller | bounds and never-raise-on-unreliable-data hold in tests; fewer badly matched sessions than the best fixed level under stated assumptions; a bounded amount of level reversal for users near a boundary | behaviour only; says nothing about recovery |
| Backend speed | analysis about 4 microseconds per sample; WebSocket round trip mean 0.76 ms, 99th percentile 1.5 ms, against one sample every 66 ms (`docs/results/performance.json`) | in-process test client on one computer; excludes network and browser pose estimation |

## 7. Discussion
The measured angle error and counting results support using the system for repetition counting and coarse feedback. Quality classification does not generalise well across datasets with the available data: five training participants cannot support deployment-grade claims, and probabilities are over-confident. Per-user calibration is the most effective single improvement found. The adaptive controller's value to real users is unknown: it was designed for safety and tested by simulation, and a study with participants would be required.
**Threats to validity.** Small, healthy, non-patient samples; binary or coarse labels; 2D angles from one camera; differences between datasets in camera, setting and labelling; thresholds that are illustrative and not clinician-reviewed; no own-webcam data collected yet (the recording tool exists); browser pose-estimation speed and end-to-end latency not measured; VR and phone use untested.

## 8. Conclusion and future work
Conclusions follow the research questions above. Future work: collect consented recordings with the project's own tool and run the external test on them; clinician review of ranges and thresholds; a study with participants before any claim about adherence or recovery; temporal models (for example recurrent networks) as a compared baseline; tested immersive VR on a headset; HTTPS and hardening for any use beyond one local computer.

## Appendices
A API reference `docs/api-documentation.md` · B exercise definitions `backend/app/exercises/definitions/` · C controller configuration `backend/app/personalization/config.json` · D dataset documentation · E full tables `docs/results/` · F user guide and manual protocol · G ethics and consent templates (use your institution's).

## Before submission
Write Chapter 2 from verified sources. Re-run the evaluation commands if any code changed (commands are in `docs/research-methodology.md`). Perform and report the manual webcam protocol, or state that it was not done. Add screenshots of each page and the architecture diagram.
