# External validation: train on rehab26-zenodo-23018128 (CC BY-NC 4.0), test on rehab24-6-videos-mediapipe-full (CC BY-NC 4.0)

Shared exercises: shoulder_abduction, sit_to_stand | train: 1110 reps, 5 participants | test: 369 reps, 9 participants (incorrect fraction 0.40)

> Binary correct-vs-incorrect only. Fixed hyperparameters; nothing tuned on the test dataset. Different people, cameras and setup (compare the two data sources in the title: they may or may not share a skeleton source), so a drop from within-dataset results is expected and informative. Preliminary and non-clinical; wide intervals with few participants.

| Method | Balanced acc. | 95% CI (participant bootstrap) | Accuracy | Incorrect: precision | recall | F1 |
|---|---|---|---|---|---|---|
| majority_class (train prior) | 0.500 | 0.500 to 0.500 | 0.404 | 0.404 | 1.000 | 0.575 |
| range_rule (threshold from train) | 0.529 | 0.482 to 0.594 | 0.615 | 0.706 | 0.081 | 0.145 |
| rf_angle_only (trained on train set) | 0.492 | 0.421 to 0.561 | 0.431 | 0.399 | 0.812 | 0.535 |
| rf_angle_only (threshold chosen on train participants) | 0.472 | 0.399 to 0.553 | 0.455 | 0.381 | 0.557 | 0.452 |
| rf_angle_plus_posture (trained on train set) | 0.579 | 0.528 to 0.631 | 0.509 | 0.449 | 0.940 | 0.607 |
| rf_angle_plus_posture (threshold chosen on train participants) | 0.598 | 0.515 to 0.672 | 0.607 | 0.512 | 0.550 | 0.531 |
| rf_angle_plus_posture_full (trained on train set) | 0.614 | 0.561 to 0.673 | 0.542 | 0.468 | 0.987 | 0.635 |
| rf_angle_plus_posture_full (threshold chosen on train participants) | 0.686 | 0.625 to 0.761 | 0.691 | 0.609 | 0.658 | 0.632 |

## By exercise (balanced accuracy)

| Method | shoulder_abduction | sit_to_stand |
|---|---|---|
| majority_class (train prior) | 0.500 | 0.500 |
| range_rule (threshold from train) | 0.540 | 0.500 |
| rf_angle_only (trained on train set) | 0.442 | 0.525 |
| rf_angle_only (threshold chosen on train participants) | 0.367 | 0.548 |
| rf_angle_plus_posture (trained on train set) | 0.522 | 0.613 |
| rf_angle_plus_posture (threshold chosen on train participants) | 0.572 | 0.630 |
| rf_angle_plus_posture_full (trained on train set) | 0.567 | 0.641 |
| rf_angle_plus_posture_full (threshold chosen on train participants) | 0.668 | 0.697 |

## By test participant (balanced accuracy, trained-on-train random forest with posture features)

- P1: 0.571
- P2: 0.516
- P3: 0.525
- P4: 0.574
- P5: 0.750
- P6: 0.504
- P7: 0.550
- P8: 0.630
- P9: 0.672

## In-domain reference: leave-one-participant-out within rehab24-6-videos-mediapipe-full (CC BY-NC 4.0) (same features, fixed params)

| Features | Balanced acc. | Accuracy | Incorrect F1 |
|---|---|---|---|
| rf_angle_only | 0.642 | 0.645 | 0.587 |
| rf_angle_plus_posture | 0.638 | 0.648 | 0.575 |
| rf_angle_plus_posture_full | 0.722 | 0.724 | 0.675 |
