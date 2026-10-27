# Adaptive difficulty controller

Code: `backend/app/personalization/controller.py` (policy, no database or camera), thresholds: `backend/app/personalization/config.json`,
glue: `backend/app/services/adaptive_service.py`, API: `backend/app/api/adaptation.py` and `sessions.py`.

This is the project's central research component. It produces **software recommendations for the next session**, not clinical decisions.
All numbers in the config are illustrative defaults for a research prototype and must be reviewed by a rehabilitation professional before any real use.

## Inputs
For each finished session: the repetitions with their **rule-based** assessment (label, score 0-1, reliable?, counted?, achieved range), plus the history of
earlier sessions of the same exercise (level, classification, action), newest first. The quality score comes from measured movement,
never from a classifier that merely predicts a high score.

## Session classification
Computed over *reliable* repetitions only (repetitions with too few valid pose frames are `insufficient_data` and are excluded):

| Class | Rule (defaults) |
|---|---|
| `insufficient` | fewer than 5 reliable repetitions, or fewer than 80% of repetitions reliable |
| `severe` | mean score < 0.30 or at least 80% of repetitions flagged |
| `poor` | mean score < 0.50 or more than 50% flagged |
| `good` | mean score >= 0.85, at most 20% flagged, target repetitions completed, range spread (std of peak progress) <= 0.15 |
| `neutral` | everything else (a deliberate dead zone between `poor` and `good`) |

## Policy
- **Increase** one level only after **2 consecutive `good` sessions at the same level** and at least 2 sessions at that level (multi-session confirmation / hysteresis). Capped at the exercise's highest level.
- **Decrease** one level only after **2 consecutive `poor`/`severe` sessions at the same level**. Never below the minimum level.
- **Pause**: a `severe` session recommends a break and never raises difficulty.
- **Maintain** in every other case. `insufficient` data never raises difficulty.
- Any other session class (neutral, insufficient, a different level) **ends a streak**, so confirmation always needs fresh, reliable evidence.
- After a change, the first session at the new level starts a new streak, so levels cannot flip-flop (minimum dwell: 2 sessions).
- **Reset** to the safe default level on request (`POST /api/adaptation/reset`), recorded as a decision.
- `config.json` is validated on load: the decrease threshold must stay below the increase threshold (dead zone), and the pause threshold must not exceed the decrease threshold.

## Outputs
`action` (increase / decrease / maintain / pause / reset), `next_level`, `target_reps`, `range_fraction` (movement-range target), `min_rep_duration_s`
(pacing target), `feedback_intensity` (more guidance after poor sessions, less after good ones), human-readable `reasons`, the metrics used, and a safety note.

## Data handling
- Only signed-in users' **non-demo** sessions create decisions and appear in analytics. Guest and synthetic demo sessions are judged on that session alone and are never saved to a history.
- Accounts store a scrypt password hash, a small profile (age range, goals text) and two preferences. Tokens are stored only as SHA-256 digests. "Delete my data" removes the account, sessions, repetitions, decisions and tokens.

## What is verified, and what is not
- Verified by automated tests (`tests/test_controller.py`, `tests/test_phase5_api.py`): bounds, one step at a time, unreliable/too-little data never raises difficulty, streak and dwell rules,
  long random histories (SYNTHETIC sessions used only to check invariants), alternating good/poor sessions never change the level, config validation, API ownership/security, demo exclusion, data deletion.
  A mutation check (weakening the policy) makes the invariant tests fail, so they do detect a broken policy.
- **Not** verified: that these thresholds are clinically appropriate, or that adaptive difficulty improves any outcome. That needs a properly designed study with real participants.
