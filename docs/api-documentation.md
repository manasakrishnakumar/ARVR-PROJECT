# API reference

The full, always-current OpenAPI documentation is served by the running backend at **http://127.0.0.1:8000/docs** (Swagger UI) and `/openapi.json`.
All endpoints are under `/api`. Errors use HTTP 404 (unknown id, or not yours), 409 (state conflict, for example a completed session), 422 (validation), 401 (sign-in required or invalid token).
Signed-in requests send `Authorization: Bearer <token>`; a token that is present but invalid is rejected, never treated as guest.

| Method and path | Auth | Purpose |
|---|---|---|
| `GET /health` | none | status, version, safety disclaimer |
| `GET /exercises`, `GET /exercises/{id}` | none | exercise definitions (illustrative targets, difficulty levels, common errors) |
| `POST /assessment/evaluate` | none | stateless: angle series in, repetitions with labels, scores and feedback out (rule-based) |
| `WS /ws/analysis?exercise_id&difficulty[&session_id&key][&calibrate=auto]` | session key | live stream: client `{t, angle\|null}`; server `hello`, `state` per frame (with `calibrating`), `calibrated` once (start/target angles), `rep` per finished repetition; with `session_id`+`key` repetitions are saved |
| `POST /auth/register`, `POST /auth/login`, `POST /auth/logout` | none / token | accounts (scrypt-hashed passwords, hashed bearer tokens, 30-day expiry) |
| `GET /me`, `PATCH /me`, `DELETE /me` | user | profile (age range, goals, two preferences); `DELETE` removes the account and all its data |
| `POST /sessions` | optional | create a session (guest if no token); returns the per-session `ws_key` once |
| `GET /sessions`, `GET /sessions/{id}`, `GET /sessions/{id}/detail` | owner / guest by id | list (signed-in users' own, demo excluded unless asked), session, or full summary with repetitions and the decision |
| `POST /sessions/{id}/repetitions` | owner | add repetitions manually (the live stream normally does this) |
| `POST /sessions/{id}/complete` | owner | finish: summary + adaptive recommendation (saved to history only for signed-in, non-demo sessions) |
| `POST /adaptation/recommend` | none | stateless policy evaluation: repetitions + optional history in, recommendation out |
| `GET /adaptation/state?exercise_id` | optional | the level suggested after the user's last session (default for guests) |
| `POST /adaptation/reset` | user | reset an exercise to the default level (recorded as a decision) |
| `GET /analytics/summary`, `GET /analytics/progress` | user | totals and per-session points; filters `exercise_id`, `from`, `to`, `include_demo` |
| `GET /analytics/export.csv?kind=sessions\|repetitions` | user | the user's own data as CSV |
| `WS /ws/relay/{room}?role=publisher\|subscriber` | room code | local pose relay: the browser publishes `{lm:[132 numbers], angle, phase, ...}` frames, other local clients (Unity) subscribe; in-memory, limits 50 rooms / 5 subscribers, 8 KB frames; close codes 4422 bad room/role, 4409 second publisher, 4429 limits |
| `GET /research/results` | none | aggregate evaluation results (JSON written by the evaluation scripts) |
| `GET /models/status` | none | whether a trained ML model artifact exists (the live loop does not use ML: see limitations) |

## WebSocket close codes
`4403` session not found, closed, or key/exercise/level mismatch · `4404` unknown exercise · `4422` unknown difficulty level.

## Scores and labels
Per repetition: `acceptable`, `insufficient_range`, `incomplete_repetition`, `too_fast`, `uncontrolled`, or `insufficient_data` (not enough reliable pose frames; never guessed). Scores are 0-1 experimental metrics from a transparent rule set, not validated outcomes.
