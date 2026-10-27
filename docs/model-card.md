# Model card: repetition quality classifier (preliminary)

- **Model**: scikit-learn RandomForestClassifier (200 trees, balanced class weights), versioned `rf-<UTC time>-<data hash>`.
- **Task**: classify one exercise repetition into acceptable / insufficient_range / incomplete_repetition / too_fast / uncontrolled / insufficient_data from 7 movement features computed from a single camera's 2D joint angle.
- **Inputs**: peak_progress, rom_fraction, duration_s, peak_velocity_norm, mean_speed_norm, extra_reversals, reliability (angles normalised by each exercise's illustrative range).
- **Output**: label, probability per class, and an explicit `uncertain` state when the top probability is below 0.5.
- **Baselines**: majority class and the configurable rule-based assessor (`app/exercise_assessment/rules.py`).
- **Evaluation**: participant-level train/test split (no leakage); accuracy, per-class precision/recall/F1, confusion matrix, macro-F1 with a participant-bootstrap 95% CI. Reports are written to `artifacts/reports/<version>/`.

## Current status
Trained **only on synthetic data**. The only reported numbers are on synthetic repetitions whose labels come from the same kind of thresholds the rule-based baseline uses, so they demonstrate that the pipeline works, not that the model works on people. The ML component is **preliminary** until it is trained and tested on real, appropriately labelled recordings from multiple participants.

## Limitations
- Single-camera 2D angles; no clinical accuracy. Not a medical device.
- Difficulty-level thresholds (rule baseline) are fixed at level 1 in the evaluation.
- Labels describe observable movement, not medical findings or safety.
- Class definitions and thresholds are illustrative and must be reviewed by a rehabilitation professional before any real use.
