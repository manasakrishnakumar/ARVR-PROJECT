# Implementation status

## Phase 1 — Environment and architecture
- [x] Environment inspected: Python 3.10.11, Git 2.55, Docker present; Node.js 24.22.1 / npm 11.19.1 installed via winget during this session; Unity not found.
- [x] Repo structure (backend, docs, scripts, datasets, artifacts)
- [x] FastAPI app, config, SQLite schema (users, sessions, repetitions)
- [x] Exercise library as JSON (5 exercises, illustrative targets)
- [x] Endpoints: GET /api/health, /api/exercises, /api/exercises/{id}, POST/GET /api/sessions, GET /api/sessions/{id}
- [x] 3 API tests pass (pytest)
- [ ] Frontend (Vite+React+TS) — blocked: Node.js not installed
- [ ] docs/architecture.md, installation.md (README covers backend only so far)

## Later phases: not started
Pose estimation, angles, repetition counter, assessment, ML, adaptation, dashboard, AR, 3D, evaluation.
