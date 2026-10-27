# Leave-one-participant-out evaluation

Data: rehab26-zenodo-23018128 (CC BY-NC 4.0) | 1084 repetitions from 5 participants (R26-P1, R26-P2, R26-P3, R26-P4, R26-P5) | labels: {'acceptable': 543, 'posture_deviation': 433, 'insufficient_range': 108}

> Small sample of healthy volunteers performing deliberate errors, one camera view per repetition, single-camera pose estimates. Preliminary: not clinical or patient data. Tuned methods choose hyperparameters/thresholds using only the training participants of each fold (nested), never the held-out person. With 5 participants the confidence intervals are wide and differences between methods should be read cautiously.

## Three-class view (acceptable / insufficient_range / posture_deviation)

| Method | Accuracy | Macro-F1 | Macro-F1 95% CI (participant bootstrap) |
|---|---|---|---|
| Majority class | 0.501 | 0.222 | 0.221 to 0.224 |
| Rule-based (illustrative thresholds) | 0.458 | 0.095 | 0.088 to 0.121 |
| Range rule, threshold tuned on training participants | 0.523 | 0.370 | 0.347 to 0.396 |
| Random forest, angle features | 0.478 | 0.432 | 0.344 to 0.526 |
| Random forest, angle features, tuned | 0.438 | 0.419 | 0.302 to 0.498 |
| Random forest, + posture features | 0.578 | 0.586 | 0.495 to 0.686 |
| Random forest, + posture features, tuned | 0.568 | 0.565 | 0.490 to 0.652 |

## Binary view (acceptable vs any incorrect)

| Method | Accuracy | Balanced acc. | Incorrect: precision | recall | F1 |
|---|---|---|---|---|---|
| Majority class | 0.501 | 0.500 | 0.000 | 0.000 | 0.000 |
| Rule-based (illustrative thresholds) | 0.497 | 0.496 | 0.478 | 0.079 | 0.136 |
| Range rule, threshold tuned on training participants | 0.547 | 0.546 | 0.798 | 0.124 | 0.214 |
| Random forest, angle features | 0.526 | 0.526 | 0.519 | 0.667 | 0.584 |
| Random forest, angle features, tuned | 0.542 | 0.542 | 0.526 | 0.826 | 0.643 |
| Random forest, + posture features | 0.608 | 0.608 | 0.583 | 0.754 | 0.658 |
| Random forest, + posture features, tuned | 0.627 | 0.628 | 0.597 | 0.778 | 0.676 |

## Per held-out participant (3-class accuracy)

| Method | R26-P1 | R26-P2 | R26-P3 | R26-P4 | R26-P5 |
|---|---|---|---|---|---|
| Majority class | 0.509 | 0.500 | 0.495 | 0.500 | 0.500 |
| Rule-based (illustrative thresholds) | 0.486 | 0.473 | 0.438 | 0.505 | 0.394 |
| Range rule, threshold tuned on training participants | 0.528 | 0.541 | 0.500 | 0.538 | 0.509 |
| Random forest, angle features | 0.481 | 0.374 | 0.338 | 0.619 | 0.575 |
| Random forest, angle features, tuned | 0.449 | 0.275 | 0.362 | 0.529 | 0.575 |
| Random forest, + posture features | 0.454 | 0.541 | 0.633 | 0.752 | 0.522 |
| Random forest, + posture features, tuned | 0.519 | 0.468 | 0.648 | 0.686 | 0.531 |

## Feature importance (mean over folds): Random forest, angle features, tuned

- rom_fraction: 0.357
- peak_progress: 0.294
- mean_speed_norm: 0.133
- peak_velocity_norm: 0.100
- duration_s: 0.092
- extra_reversals: 0.021
- reliability: 0.002

## Feature importance (mean over folds): Random forest, + posture features, tuned

- rom_fraction: 0.165
- peak_progress: 0.106
- torso_tilt_dev_mean: 0.083
- rom3d_deg: 0.079
- torso_tilt_dev_max: 0.075
- heel_lift_dev_max: 0.065
- lr_angle_asym_mean_deg: 0.064
- knee_valgus_dev_max: 0.054
- knee_over_toe_dev_max: 0.047
- mean_speed_norm: 0.043

Confusion matrix (Random forest, angle features, tuned; rows = true, cols = predicted; order: acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data, posture_deviation)
```
 140  188    0    0    0    0  215
  15   82    0    0    0    0   11
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
  79  101    0    0    0    0  253
```

Confusion matrix (Random forest, + posture features, tuned; rows = true, cols = predicted; order: acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data, posture_deviation)
```
 259   62    0    0    0    0  222
  16   88    0    0    0    0    4
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
 104   60    0    0    0    0  269
```
