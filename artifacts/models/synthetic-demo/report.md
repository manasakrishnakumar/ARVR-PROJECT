# Evaluation report rf-20261027-180833-185cb8d1

> **SYNTHETIC DATA ONLY.** Labels come from a generator, not human annotation. These numbers only show the pipeline runs; they say nothing about accuracy on real people, and the generator mirrors the rule thresholds, so they cannot show which method is better in practice.

Data sources: synthetic | rows: 720 | split: by participant (21 train / 9 test participants; 504 / 216 rows) | seed 0

| Method | Accuracy | Macro-F1 | Macro-F1 95% CI (participant bootstrap) |
|---|---|---|---|
| majority_class | 0.167 | 0.048 | 0.048 to 0.048 |
| rule_based | 0.856 | 0.856 | 0.778 to 0.904 |
| random_forest | 0.954 | 0.953 | 0.905 to 0.986 |

## Per-class: rule_based

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| acceptable | 0.80 | 0.44 | 0.57 | 36 |
| insufficient_range | 1.00 | 0.81 | 0.89 | 36 |
| incomplete_repetition | 1.00 | 1.00 | 1.00 | 36 |
| too_fast | 1.00 | 1.00 | 1.00 | 36 |
| uncontrolled | 0.54 | 0.89 | 0.67 | 36 |
| insufficient_data | 1.00 | 1.00 | 1.00 | 36 |
| posture_deviation | 0.00 | 0.00 | 0.00 | 0 |
| incorrect_unspecified | 0.00 | 0.00 | 0.00 | 0 |

Confusion matrix (rule_based; rows = true, columns = predicted; order: acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data, posture_deviation, incorrect_unspecified)

```
  16    0    0    0   20    0    0    0
   0   29    0    0    7    0    0    0
   0    0   36    0    0    0    0    0
   0    0    0   36    0    0    0    0
   4    0    0    0   32    0    0    0
   0    0    0    0    0   36    0    0
   0    0    0    0    0    0    0    0
   0    0    0    0    0    0    0    0
```

## Per-class: random_forest

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| acceptable | 1.00 | 0.72 | 0.84 | 36 |
| insufficient_range | 1.00 | 1.00 | 1.00 | 36 |
| incomplete_repetition | 1.00 | 1.00 | 1.00 | 36 |
| too_fast | 1.00 | 1.00 | 1.00 | 36 |
| uncontrolled | 0.78 | 1.00 | 0.88 | 36 |
| insufficient_data | 1.00 | 1.00 | 1.00 | 36 |
| posture_deviation | 0.00 | 0.00 | 0.00 | 0 |
| incorrect_unspecified | 0.00 | 0.00 | 0.00 | 0 |

Confusion matrix (random_forest; rows = true, columns = predicted; order: acceptable, insufficient_range, incomplete_repetition, too_fast, uncontrolled, insufficient_data, posture_deviation, incorrect_unspecified)

```
  26    0    0    0   10    0    0    0
   0   36    0    0    0    0    0    0
   0    0   36    0    0    0    0    0
   0    0    0   36    0    0    0    0
   0    0    0    0   36    0    0    0
   0    0    0    0    0   36    0    0
   0    0    0    0    0    0    0    0
   0    0    0    0    0    0    0    0
```
