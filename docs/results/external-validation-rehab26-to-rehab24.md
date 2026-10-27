# External validation: train on rehab26-zenodo-23018128 (CC BY-NC 4.0), test on rehab24-6-zenodo-13305826 (CC BY-NC 4.0)

Shared exercises: shoulder_abduction, sit_to_stand | train: 1110 reps, 5 participants | test: 369 reps, 9 participants (incorrect fraction 0.40)

> Binary correct-vs-incorrect only. Fixed hyperparameters; nothing tuned on the test dataset. Different people, cameras and skeleton source (the test skeleton may come from a different system than the training one), so a drop from within-dataset results is expected and informative. Preliminary and non-clinical; wide intervals with few participants.

| Method | Balanced acc. | 95% CI (participant bootstrap) | Accuracy | Incorrect: precision | recall | F1 |
|---|---|---|---|---|---|---|
| majority_class (train prior) | 0.500 | 0.500 to 0.500 | 0.404 | 0.404 | 1.000 | 0.575 |
| range_rule (threshold from train) | 0.528 | 0.482 to 0.591 | 0.615 | 0.733 | 0.074 | 0.134 |
| rf_angle_only (trained on train set) | 0.532 | 0.485 to 0.583 | 0.477 | 0.424 | 0.819 | 0.558 |
| rf_angle_plus_posture (trained on train set) | 0.608 | 0.561 to 0.656 | 0.537 | 0.465 | 0.980 | 0.631 |

## By exercise (balanced accuracy)

| Method | shoulder_abduction | sit_to_stand |
|---|---|---|
| majority_class (train prior) | 0.500 | 0.500 |
| range_rule (threshold from train) | 0.540 | 0.500 |
| rf_angle_only (trained on train set) | 0.510 | 0.509 |
| rf_angle_plus_posture (trained on train set) | 0.522 | 0.664 |

## By test participant (balanced accuracy, trained-on-train random forest with posture features)

- P1: 0.640
- P2: 0.500
- P3: 0.650
- P4: 0.557
- P5: 0.625
- P6: 0.500
- P7: 0.675
- P8: 0.575
- P9: 0.707

## In-domain reference: leave-one-participant-out within rehab24-6-zenodo-13305826 (CC BY-NC 4.0) (same features, fixed params)

| Features | Balanced acc. | Accuracy | Incorrect F1 |
|---|---|---|---|
| rf_angle_only | 0.609 | 0.612 | 0.552 |
| rf_angle_plus_posture | 0.689 | 0.694 | 0.637 |
