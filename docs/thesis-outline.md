# M.Tech thesis outline (suggested)

A working draft of Chapters 1 and 3-8 with the real results is in `docs/thesis-draft.md` (Chapter 2 must be written from sources you verify).

Title: *An AI-Driven Adaptive AR/VR Framework for Personalized Rehabilitation Using Vision-Based Human Pose Estimation*
(Be accurate about scope in the thesis: the implemented system is a **desktop/web, camera-only adaptive rehabilitation framework**; AR/VR presentation modes are proposed extensions unless you build and test them.)

## Front matter
Abstract (what was built, how it was evaluated, the honest headline results, limits) · acknowledgements · declaration · contents · figures · tables · abbreviations.

## 1. Introduction
1.1 Background and motivation · 1.2 Problem statement · 1.3 Objectives · 1.4 Research questions (RQ1-RQ6 in `docs/research-methodology.md`) · 1.5 Contributions (the statement in section 8 of the methodology) · 1.6 Scope and non-goals (not a medical device; no clinical validation) · 1.7 Thesis structure.

## 2. Literature review (outline: fill from verified primary sources)
2.1 Home and tele-rehabilitation; adherence and feedback · 2.2 Vision-based human pose estimation (MediaPipe, others; 2D versus 3D; accuracy limits) · 2.3 Exercise assessment and action quality assessment (rule-based, classical ML, deep, temporal models) · 2.4 Rehabilitation datasets (UI-PRMD, KIMORE, IntelliRehabDS, REHAB24-6, REHAB26-ViewAngles; labels, sensors, licences) · 2.5 Adaptive difficulty and personalization (dynamic difficulty adjustment, safety constraints, hysteresis) · 2.6 AR/VR in rehabilitation (benefits, evidence, cybersickness, accessibility) · 2.7 Gaps this work addresses.

## 3. Requirements and system design
3.1 Requirements, constraints (laptop, webcam, CPU, open source) · 3.2 Architecture (`docs/architecture.md`) · 3.3 Pose estimation layer and coordinate conventions · 3.4 Exercise library design · 3.5 Privacy and safety design · 3.6 Database design.

## 4. Methods
4.1 Joint angles and signal conditioning · 4.2 Repetition counting · 4.3 Feature engineering (angle and posture/depth features) · 4.4 Rule-based assessment · 4.5 Machine-learning pipeline · 4.6 Adaptive controller (policy, config, safety proofs-by-test) · 4.7 Feedback generation · 4.8 Session analytics.

## 5. Implementation
5.1 Backend (FastAPI, SQLite, WebSocket) · 5.2 Frontend (React, TypeScript, charts) · 5.3 Evaluation toolchain and own-recording tool · 5.4 Testing strategy (unit, property, API, mutation check, frontend tests, what needs hardware).

## 6. Evaluation
6.1 Datasets and licences (`docs/dataset-documentation.md`) · 6.2 Protocol: participant-level splits, nested tuning, bootstrap intervals, external validation · 6.3 Angle accuracy · 6.4 Repetition counting · 6.5 Movement-quality classification (baselines, ablation, leave-one-participant-out, external, calibration) · 6.6 Adaptive controller: behaviour tests and simulation · 6.7 System performance (frame rate, latency) · 6.8 Results from your own recordings (if collected) · 6.9 Discussion and threats to validity.

## 7. Results summary and discussion
Headline numbers (from `docs/results/`), what they do and do not mean, comparison with published work (verified citations), limitations.

## 8. Conclusion and future work
Conclusions per RQ; future work list (methodology section 10); recommendations for a clinical study.

## Appendices
A. API reference · B. Exercise definitions · C. Adaptive controller configuration · D. Dataset documentation · E. Full result tables · F. User guide and manual test protocol · G. Ethics and consent templates (for the record-data tool; use your institution's templates).

## Checklist before submission
- Every number traced to a file in `docs/results/` or a test.
- Claims match `docs/limitations-and-safety.md` (no recovery or clinical claims).
- Dataset citations and licences verified on their Zenodo pages.
- Real-webcam test (`docs/user-guide.md`) performed and written up, or stated as not done.
- Screenshots of every page; architecture and data-flow diagrams (Mermaid in `docs/architecture.md`).
