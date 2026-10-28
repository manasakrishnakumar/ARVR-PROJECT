# Results summary (for the thesis)

All numbers are **preliminary, non-clinical** and come from the aggregate files in this folder (no participant names; participants are R26-P1 to R26-P5). Public datasets are CC BY-NC 4.0 and are not redistributed. Synthetic data is never evidence.

| Question | Method | Result | Where |
|---|---|---|---|
| How accurate is the browser-measured joint angle? | MediaPipe on REHAB24-6 video vs. motion-capture angle, 49,171 frames | MAE 8.02 deg, RMSE 14.24 deg, bias -2.14 deg, r 0.97 | angle-accuracy.json |
| Does repetition counting match labelled repetitions? | REHAB26, boundary matching | F1 0.90 without, 0.97 with per-user range calibration | counting.json |
| Does a movement-quality model transfer to a new dataset? | Train REHAB26, test REHAB24-6 (mocap) | balanced accuracy 0.49 (angle only), 0.61 (full features), 0.686 (95% CI 0.625-0.761) with a threshold chosen on training data only | external-mocap.json |
| Same, with the app's own pose pipeline | MediaPipe on the REHAB24-6 videos | see report | external-like-for-like.json |
| In-domain reference | leave-one-participant-out, REHAB26 | balanced accuracy about 0.72 | lopo-rehab26.json |
| Are the probabilities trustworthy? | Brier score, calibration error | over-confident: mean predicted 0.70 vs 0.40 observed | external-mocap.json |
| How fast is the backend? | analysis cost and WebSocket round trip, in-process, one computer | analysis about 4 microseconds per sample; round trip mean 0.76 ms, 99th percentile 1.5 ms (budget: 66 ms per sample); excludes network and browser pose estimation | performance.json |
| Does the adaptive controller behave safely? | Simulation with made-up user models | bounded, no unsafe increases; says nothing about benefit to real people | adaptive-simulation.json |

## Reading these honestly
- Transfer between datasets is modest; the in-domain figure is not what a new user should expect.
- The model is over-confident, so its probabilities must not be shown to users as certainty.
- No patients took part, so there is no evidence of rehabilitation benefit.
- Thresholds have not been reviewed by a clinician.
