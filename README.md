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
