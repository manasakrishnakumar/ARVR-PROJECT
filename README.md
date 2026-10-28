# ARVR — An AI-Driven Adaptive AR/VR Framework for Personalized Rehabilitation Using Vision-Based Human Pose Estimation

Research prototype. **Not a medical device; not clinically validated.** Follow guidance from your qualified rehabilitation professional. Runs locally; no video is uploaded or stored by default.

## Backend quick start (Windows PowerShell)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
.\.venv\Scripts\python -m pytest -q
```
Database (SQLite) is created automatically on startup. Exercise definitions live in `backend/app/exercises/definitions/*.json` (illustrative targets only).

See `docs/implementation-status.md` for progress.

## Frontend quick start
```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1   # http://127.0.0.1:5173 (start the backend first)
npm run build
```

## Pages
`/` landing · `/exercises` library · `/session` live camera session (or synthetic demo) · `/room` 3D room · `/ar` AR camera overlay · `/analysis` pose analysis · `/collect` record data · `/sessions/:id` session summary · `/dashboard` progress charts and CSV export (signed-in) · `/research` evaluation results · `/settings` privacy, profile, data export/deletion · `/account` sign in / create account. Guest mode works without an account but saves nothing.

## Useful commands (from `backend`, PowerShell)
```powershell
.\.venv\Scripts\python -m pytest -q                                   # all backend tests
.\.venv\Scripts\python -m app.ml.cli generate                         # SYNTHETIC sample dataset
..\scripts\train_model.ps1                                            # train + evaluate on the synthetic sample
.\.venv\Scripts\python -m app.ml.cli lopo --data <reps.csv> --json ..\docs\results\x.json   # leave-one-participant-out
```
Real research datasets (REHAB26, REHAB24-6; CC BY-NC 4.0) are not included: see `docs/dataset-documentation.md` for how they were obtained and imported. Results: `docs/results/`. Progress and honest limitations: `docs/implementation-status.md`, `docs/adaptive-controller.md`, `docs/model-card.md`.

## Documentation
[Architecture](docs/architecture.md) · [Installation](docs/installation.md) (or run `scripts\setup.ps1`) · [User guide and manual webcam test](docs/user-guide.md) · [Research methodology and contribution](docs/research-methodology.md) · [API reference](docs/api-documentation.md) · [Limitations and safety](docs/limitations-and-safety.md) · [Adaptive controller](docs/adaptive-controller.md) · [Datasets](docs/dataset-documentation.md) · [Model card](docs/model-card.md) · [Thesis outline](docs/thesis-outline.md) · [Implementation status](docs/implementation-status.md)
