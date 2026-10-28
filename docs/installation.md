# Installation and running (Windows PowerShell)

## 1. Prerequisites
| Tool | Version used | Check |
|---|---|---|
| Python | 3.10+ | `python --version` |
| Node.js + npm | Node 24 LTS | `node --version` (install from https://nodejs.org, or `winget install OpenJS.NodeJS.LTS`; open a new terminal afterwards) |
| Git | any recent | `git --version` |
| Webcam | any | optional: the synthetic demo needs none |

No GPU, Docker, Unity or VR headset is needed. (No Docker setup is provided; the plain workflow below is the supported one.)
Keep the project in a **short path** (for example your Desktop): very long folder names can break `pip install` on Windows.

## Quick setup (does steps 2-4 for you)
```powershell
.\scripts\setup.ps1        # from the repository root: Python venv + backend packages, npm install, MediaPipe runtime files, pose model
```
Then start the two servers as shown in steps 2 and 4. The manual steps below explain what the script does.

## 2. Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs  (interactive API docs)
```
The SQLite database (`backend/arvr.db`) is created automatically on first start; an older database is upgraded in place.
Reset it (deletes all accounts and sessions): `.\.venv\Scripts\python -c "from app.database.db import reset_db; reset_db()"`.
Use another database file with the environment variable `ARVR_DATABASE_URL=sqlite:///C:/path/to/file.db`.

## 3. Pose model (needed for the real camera; the demo works without it)
```powershell
.\scripts\download_pose_model.ps1        # from the repository root; saves frontend\public\models\pose_landmarker_lite.task (about 6 MB)
```
It downloads Google's official MediaPipe model. The WASM runtime files are copied to `frontend\public\wasm\` by the setup step below.

## 4. Frontend
```powershell
cd frontend
npm install
New-Item -ItemType Directory -Force public\wasm | Out-Null                    # once: the MediaPipe runtime files are served locally
Copy-Item node_modules\@mediapipe\tasks-vision\wasm\* public\wasm\ -Force
npm run dev -- --host 127.0.0.1           # http://127.0.0.1:5173  (start the backend first)
```
`npm run build` makes a production build; `npm test` runs the frontend tests.

## 5. Camera permission
Open the site, choose **Start camera**, and allow camera access when the browser asks. Use `http://127.0.0.1` or `http://localhost` (browsers allow cameras only on secure or local addresses). If you pressed "Block" once: click the camera icon in the address bar and allow it. The page `/analysis` shows permission state, resolution, processing speed and landmark confidence, which helps to check your setup.

## 6. Tests
```powershell
cd backend; .\.venv\Scripts\python -m pytest -q           # backend: unit, API, WebSocket, persistence, ML, evaluation tests
cd ..\frontend; npm test                                  # frontend: angle maths, API client, components, pages
```
Tests need **no camera and no downloaded datasets**: they use synthetic sequences and mocks. Tests that need real hardware (webcam on your laptop) are manual: see `docs/user-guide.md`.

## 7. Machine learning and evaluation (optional)
```powershell
.\scripts\train_model.ps1                                  # generates the SYNTHETIC sample dataset and trains/evaluates (pipeline check only)
cd backend
.\.venv\Scripts\python -m app.ml.cli lopo --data <reps.csv> --json ..\docs\results\x.json
.\.venv\Scripts\python -m app.ml.cli external --train <a.csv> --test <b.csv> --report r.md --json ..\docs\results\y.json
.\.venv\Scripts\python -m app.ml.cli count-eval --json ..\docs\results\counting.json
.\.venv\Scripts\python -m app.personalization.simulation --json ..\docs\results\adaptive-simulation.json
```
The real research datasets are **not included** (licence, size). `docs/dataset-documentation.md` describes how REHAB26-ViewAngles and REHAB24-6 were obtained and imported, and `backend/requirements-video.txt` lists the optional packages for running pose estimation on videos.

## 8. Troubleshooting
| Problem | Fix |
|---|---|
| `npm` not found | open a **new** terminal after installing Node |
| `pip install` fails with "filename too long" | move the project to a shorter folder path |
| Page says it cannot reach the backend | start `uvicorn` first; the frontend proxies `/api` to port 8000 |
| "Pose model not found" | run `scripts\download_pose_model.ps1`, then reload |
| Camera permission denied | allow the camera for the site in the browser; close other apps using the camera |
| Reps are not counted but the skeleton shows | check the backend is running; the page shows a red message if the live stream failed |
| Counts look wrong for your body or camera angle | the exercise ranges are illustrative defaults; see "Calibration" in `docs/limitations-and-safety.md` |
| Frame rate below 10 per second | close other applications, improve lighting, use a smaller camera resolution; see `/analysis` |
| Port already in use | stop the old server (`Get-NetTCPConnection -LocalPort 8000` shows the process) or use another port |

## Docker (optional, untested)
`docker compose up --build` from the repository root should serve the app at http://localhost:8080 (nginx proxies `/api` to the backend; the database lives in a Docker volume). The files are written but **have not been built or run**: the Docker engine was not running when they were added. The MediaPipe model and wasm files are git-ignored: run `scripts\download_pose_model.ps1` before building so the camera pages work.
