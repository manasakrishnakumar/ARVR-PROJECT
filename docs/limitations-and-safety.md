# Limitations and safety

## Status in one line
A working research prototype with a tested software pipeline and **preliminary, non-clinical** evaluations. It has **not** been validated on patients, reviewed by a clinician, or shown to improve recovery.

## Safety statements built into the product
- A disclaimer is visible on every page; the landing page and recommendation cards repeat it. Nothing in the app diagnoses, prescribes, or judges whether an exercise is safe for a person.
- Exercise targets are **illustrative** and are labelled so. Difficulty changes are conservative software suggestions with reasons, never automatic prescriptions, and never based on unreliable measurements.
- When the system cannot measure reliably it says so (`insufficient_data`, "pose not detected clearly") instead of guessing.
- The user is told to stop if there is discomfort and to follow their professional's guidance.

## What has and has not been verified
| Area | Verified | Not verified |
|---|---|---|
| Software behaviour | 177 automated tests (147 backend, 30 frontend): angle maths, missing/low-confidence landmarks, counter, assessment, controller safety bounds, API validation and ownership, persistence, WebSocket, data deletion, importers, evaluation code | behaviour on your particular camera, light and body: run the manual protocol in `docs/user-guide.md` |
| Real camera | pose model runs in the browser; skeleton overlay checked on real video frames (REHAB24-6) | **the live webcam path has not been run on a real webcam by the author**; the demo mode and recorded videos were used |
| Joint angles | against optical motion capture on 49,171 frames of REHAB24-6: MAE 8.0°, RMSE 14.2°, bias -2.1°, r = 0.97; frames aligned (lag 0); shoulder abduction MAE 8.9° (bias -7.5°), squat 6.8° (bias +5.2°); one camera 9.0°, the other 4.3° | accuracy for other bodies, clothing, cameras, or true 3D angles. Part of the error is definitional (mocap joint centres vs MediaPipe landmarks). These are 2D image-plane angles, not clinical measurements |
| Repetition counting | against labelled repetition boundaries in two public datasets | people with impaired movement, slow/partial repetitions, other setups. With illustrative angles F1 0.90 and mean count error 1.0 on REHAB26; calibrating the range from the recording itself gives F1 0.97 and error 0.2 (the app does not yet calibrate live) |
| Movement-quality ML | independent-dataset test (train REHAB26, test REHAB24-6, MediaPipe on both): balanced accuracy 0.69 (95% CI 0.63 to 0.76) with a threshold chosen on training data only; 0.61 with the default threshold; angle-only features are at chance | clinical usefulness; real patients; the ML model is **not used in the live loop** (see below) |
| Adaptive controller | safety invariants, hysteresis, no flip-flopping beyond a measured bound; simulation (stated assumptions) | **any benefit for real people**, clinical appropriateness of thresholds |

## Known limitations
1. **Single camera, 2D.** Angles depend on viewpoint. Posture errors (trunk lean, shoulder shrug, knees caving in) cannot be seen from one joint angle; posture features help only modestly, and arm abduction transfers poorly across datasets.
2. **Illustrative ranges.** Start/target angles per exercise are illustrative defaults and do not match every body or camera angle. Counting improves when the range is calibrated per recording; a live calibration step is the recommended next change and is **not implemented**.
3. **Small, healthy, scripted data.** The public datasets used have 5 and 10 volunteers performing deliberate errors. Results have wide intervals and say nothing about patients or about naturally occurring errors.
4. **ML not in the live loop, by design.** The live pipeline sends only one joint angle, with which the ML features are at chance. Using ML live would require sending landmarks and a model that is better calibrated: its probabilities are currently over-confident (mean predicted probability 0.70 vs observed incorrect rate 0.40 on the external set) and are not shown to users.
5. **Take-level labels** in the own-recording tool assume every repetition in a take was done as intended.
6. **Thresholds** in `backend/app/personalization/config.json` and the rule set are illustrative and unreviewed by a clinician.
7. **Local prototype security.** Single-user, local-network assumptions: no rate limiting, no HTTPS, tokens in browser storage, a per-session key in the WebSocket URL. Not suitable for exposure to the internet.
8. **Built but limited:** a desktop 3D room and an AR *camera overlay* (not immersive AR) exist and were checked with the synthetic demo only; a Unity client scaffold exists but has not been compiled or run. **Not built:** immersive VR/WebXR sessions, LSTM/GRU temporal model. No headset has been used.

## What would change these statements
A study with consent and ethics approval on the target population, labelled by clinicians; live range calibration; a clinician review of thresholds and error definitions; and tests on real hardware by the person who will use the system.
