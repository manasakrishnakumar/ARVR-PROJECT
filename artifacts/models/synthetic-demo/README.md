# Synthetic demo model (pipeline check only)

**SYNTHETIC DATA ONLY.** This Random Forest was trained on `datasets/sample/synthetic_reps.csv`: 720 repetitions from 30 *simulated*
participants whose labels come from a generator, not from people. It exists to show that the training, versioning and inference pipeline
works end to end. It says **nothing** about accuracy on real human movement, and it is not used by the live session loop.

- Reproduce: `.\scripts\train_model.ps1` (from the repository root). Numbers differ slightly between runs because the version carries a timestamp; the seed is fixed.
- Contents: `model.joblib` (scikit-learn 1.7.2 RandomForestClassifier), `metadata.json` (features, classes, data hash, `synthetic_only: true`), `report.md` (evaluation on held-out simulated participants, with its own synthetic-data warning).
- Use it: `MLAssessor.load(Path("artifacts"), version="synthetic-demo")` (see `backend/app/ml/inference.py`). `GET /api/models/status` reads the newest locally trained model (`artifacts/models/LATEST`), not this one.
- **Security note:** `.joblib` files are Python pickles. Only load model files you trust or built yourself; do not load a model file from an untrusted source.
- Real-data results are in `docs/results/` and on the app's Research page. They come from evaluations, not from this model.