# Leave-one-participant-out evaluation

Data: rehab26-zenodo-23018128 (CC BY-NC 4.0) | 1665 repetitions from 5 participants (R26-P1, R26-P2, R26-P3, R26-P4, R26-P5) | labels: {'acceptable': 832, 'posture_deviation': 722, 'insufficient_range': 111}

> Small sample of healthy volunteers performing deliberate errors, one camera view per repetition, single-camera pose estimates. Preliminary: not clinical or patient data. Tuned methods choose hyperparameters/thresholds using only the training participants of each fold (nested), never the held-out person. With 5 participants the confidence intervals are wide and differences between methods should be read cautiously.

## Three-class view (acceptable / insufficient_range / posture_deviation)

| Method | Accuracy | Macro-F1 | Macro-F1 95% CI (participant bootstrap) |
|---|---|---|---|
| Majority class | 0.500 | 0.222 | 0.222 to 0.223 |
| Rule-based (illustrative thresholds) | 0.463 | 0.099 | 0.093 to 0.124 |
| Range rule, threshold tuned on training participants | 0.505 | 0.344 | 0.318 to 0.359 |
| Random forest, angle features | 0.527 | 0.457 | 0.375 to 0.533 |
| Random forest, angle features, tuned | 0.465 | 0.426 | 0.341 to 0.488 |
| Random forest, + posture features | 0.631 | 0.612 | 0.560 to 0.673 |
| Random forest, + posture features, tuned | 0.638 | 0.602 | 0.554 to 0.677 |

## Binary view (acceptable vs any incorrect)

| Method | Accuracy | Balanced acc. | Incorrect: precision | recall | F1 |
|---|---|---|---|---|---|
| Majority class | 0.500 | 0.500 | 0.000 | 0.000 | 0.000 |
| Rule-based (illustrative thresholds) | 0.506 | 0.506 | 0.536 | 0.089 | 0.152 |
| Range rule, threshold tuned on training participants | 0.523 | 0.523 | 0.697 | 0.083 | 0.148 |
| Random forest, angle features | 0.559 | 0.558 | 0.547 | 0.683 | 0.608 |
| Random forest, angle features, tuned | 0.560 | 0.560 | 0.539 | 0.831 | 0.654 |
| Random forest, + posture features | 0.655 | 0.655 | 0.619 | 0.803 | 0.699 |
| Random forest, + posture features, tuned | 0.685 | 0.685 | 0.652 | 0.794 | 0.716 |

## Per held-out participant (3-class accuracy)

| Method | R26-P1 | R26-P2 | R26-P3 | R26-P4 | R26-P5 |
|---|---|---|---|---|---|
| Majority class | 0.502 | 0.496 | 0.498 | 0.500 | 0.503 |
| Rule-based (illustrative thresholds) | 0.468 | 0.478 | 0.444 | 0.500 | 0.426 |
| Range rule, threshold tuned on training participants | 0.495 | 0.522 | 0.480 | 0.515 | 0.509 |
| Random forest, angle features | 0.492 | 0.490 | 0.420 | 0.633 | 0.601 |
| Random forest, angle features, tuned | 0.477 | 0.337 | 0.408 | 0.527 | 0.574 |
| Random forest, + posture features | 0.562 | 0.642 | 0.595 | 0.761 | 0.598 |
| Random forest, + posture features, tuned | 0.571 | 0.597 | 0.631 | 0.761 | 0.633 |

## Feature importance (mean over folds): Random forest, angle features, tuned

- peak_progress: 0.355
- rom_fraction: 0.270
- duration_s: 0.120
- mean_speed_norm: 0.120
- peak_velocity_norm: 0.093
- extra_reversals: 0.040
- reliability: 0.003

## Feature importance (mean over folds): Random forest, + posture features, tuned

- peak_progress: 0.153
- rom_fraction: 0.124
- torso_tilt_dev_mean: 0.078
- rom3d_deg: 0.074
- torso_tilt_dev_max: 0.064
- duration_s: 0.056
- mean_speed_norm: 0.054
- elbow_bend_min_3d_deg: 0.051
- peak3d_minus_2d_progress: 0.049
- lr_angle_asym_mean_deg: 0.043

Confusion matrix (Random forest, angle features, tuned; rows = true, cols = predicted; order: acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data, posture_deviation)
```
 240  242    0    0    0    0  350
  17   88    0    0    0    0    6
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
 124  152    0    0    0    0  446
```

Confusion matrix (Random forest, + posture features, tuned; rows = true, cols = predicted; order: acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data, posture_deviation)
```
 479   76    0    0    0    0  277
  18   85    0    0    0    0    8
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
   0    0    0    0    0    0    0
 154   69    0    0    0    0  499
```
