# Leave-one-participant-out evaluation

Data: rehab26-zenodo-23018128 (CC BY-NC 4.0) | 1665 repetitions from 5 participants (R26-P1, R26-P2, R26-P3, R26-P4, R26-P5) | labels: {'acceptable': 832, 'posture_deviation': 722, 'insufficient_range': 111}

> Small sample of healthy volunteers performing deliberate errors, one camera view per repetition, single-camera pose estimates. Preliminary: not clinical or patient data. Tuned methods choose hyperparameters/thresholds using only the training participants of each fold (nested), never the held-out person. With 5 participants the confidence intervals are wide and differences between methods should be read cautiously.

## Three-class view (acceptable / insufficient_range / posture_deviation)

| Method | Accuracy | Macro-F1 | Macro-F1 95% CI (participant bootstrap) |
|---|---|---|---|
| Majority class | 0.500 | 0.222 | 0.222 to 0.223 |
| Rule-based (illustrative thresholds) | 0.433 | 0.112 | 0.105 to 0.120 |
| Range rule, threshold tuned on training participants | 0.512 | 0.368 | 0.306 to 0.416 |
| Random forest, angle features | 0.476 | 0.389 | 0.321 to 0.447 |
| Random forest, angle features, tuned | 0.340 | 0.310 | 0.246 to 0.356 |
| Random forest, + posture features | 0.633 | 0.603 | 0.554 to 0.662 |
| Random forest, + posture features, tuned | 0.640 | 0.627 | 0.574 to 0.679 |

## Binary view (acceptable vs any incorrect)

| Method | Accuracy | Balanced acc. | Incorrect: precision | recall | F1 |
|---|---|---|---|---|---|
| Majority class | 0.500 | 0.500 | 0.000 | 0.000 | 0.000 |
| Rule-based (illustrative thresholds) | 0.483 | 0.483 | 0.439 | 0.121 | 0.190 |
| Range rule, threshold tuned on training participants | 0.525 | 0.525 | 0.750 | 0.076 | 0.137 |
| Random forest, angle features | 0.523 | 0.523 | 0.517 | 0.707 | 0.597 |
| Random forest, angle features, tuned | 0.500 | 0.499 | 0.500 | 0.851 | 0.630 |
| Random forest, + posture features | 0.655 | 0.655 | 0.619 | 0.803 | 0.699 |
| Random forest, + posture features, tuned | 0.676 | 0.676 | 0.645 | 0.786 | 0.708 |

## Per held-out participant (3-class accuracy)

| Method | R26-P1 | R26-P2 | R26-P3 | R26-P4 | R26-P5 |
|---|---|---|---|---|---|
| Majority class | 0.502 | 0.496 | 0.498 | 0.500 | 0.503 |
| Rule-based (illustrative thresholds) | 0.456 | 0.457 | 0.381 | 0.452 | 0.420 |
| Range rule, threshold tuned on training participants | 0.483 | 0.540 | 0.492 | 0.530 | 0.515 |
| Random forest, angle features | 0.441 | 0.493 | 0.450 | 0.552 | 0.447 |
| Random forest, angle features, tuned | 0.369 | 0.203 | 0.378 | 0.315 | 0.435 |
| Random forest, + posture features | 0.613 | 0.639 | 0.628 | 0.718 | 0.568 |
| Random forest, + posture features, tuned | 0.595 | 0.615 | 0.695 | 0.724 | 0.574 |

## Feature importance (mean over folds): Random forest, angle features, tuned

- peak_progress: 0.276
- rom_fraction: 0.231
- duration_s: 0.176
- mean_speed_norm: 0.163
- peak_velocity_norm: 0.101
- extra_reversals: 0.051
- reliability: 0.001

## Feature importance (mean over folds): Random forest, + posture features, tuned

- rom3d_deg: 0.096
- peak_progress: 0.092
- torso_tilt_dev_mean: 0.082
- lr_angle_asym_mean_deg: 0.075
- rom_fraction: 0.074
- torso_tilt_dev_max: 0.064
- heel_lift_dev_max: 0.057
- duration_s: 0.056
- knee_valgus_dev_max: 0.054
- peak3d_minus_2d_progress: 0.054

Confusion matrix (Random forest, angle features, tuned; rows = true, cols = predicted; order: acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data, posture_deviation, incorrect_unspecified)
```
 123  380    0    0    0    0  329    0
  12   80    0    0    0    0   19    0
   0    0    0    0    0    0    0    0
   0    0    0    0    0    0    0    0
   0    0    0    0    0    0    0    0
   0    0    0    0    0    0    0    0
 112  247    0    0    0    0  363    0
   0    0    0    0    0    0    0    0
```

Confusion matrix (Random forest, + posture features, tuned; rows = true, cols = predicted; order: acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data, posture_deviation, incorrect_unspecified)
```
 471   59    0    0    0    0  302    0
  12   94    0    0    0    0    5    0
   0    0    0    0    0    0    0    0
   0    0    0    0    0    0    0    0
   0    0    0    0    0    0    0    0
   0    0    0    0    0    0    0    0
 166   55    0    0    0    0  501    0
   0    0    0    0    0    0    0    0
```
