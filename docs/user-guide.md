# User guide

ARVR is a **research prototype, not a medical device**. It cannot tell whether an exercise is safe for you. Follow your qualified rehabilitation professional's guidance, and stop if you feel discomfort.

## Try it without an account (guest mode)
1. Open **Exercises** and pick one, or go straight to **Live session**.
2. Press **Synthetic demo** to see how it works with no camera (a drawn figure; only elbow flexion moves), or **Start camera** and allow camera access.
3. Stand where your whole body (or at least the exercising limb and the joints around it) is visible, in good light, 1.5 to 3 metres from the camera. Face the camera for arm exercises; stand side-on for squats and sit-to-stand.
4. Move. The page shows the skeleton, the current phase, repetitions against the target, the joint angle, and one short tip after each repetition. Turn on **Audio feedback** for spoken tips.
5. Press **Stop and save**: you get a summary and a suggested level for next time. Guest and demo sessions are **not saved**; the suggestion uses that session alone.

## With an account
Create one on **Sign in** (a username and a password you use nowhere else; no medical details). Your sessions and suggestions are saved on this computer. The **Live session** page then pre-selects the level suggested after your last session; you may choose another level, and **Reset to default level** is always available.

## What the suggestions mean
After each real session the app judges only the repetitions it could measure reliably: good (steady, complete, few flagged), moderate, poor, or very poor. It raises the level by one step only after **two good sessions in a row** at the same level, lowers it only after **two poor sessions in a row**, suggests a break after a very difficult session, and never raises the level when it could not measure you reliably. Every suggestion lists its reasons. It is a suggestion, not a prescription. Details: `docs/adaptive-controller.md`.

## Pages
| Page | What it is for |
|---|---|
| Home | overview and the safety statement |
| Exercises | the library: illustrative range diagrams, levels, what the system can notice |
| Live session | the exercise session described above |
| Pose analysis | check your camera setup: skeleton, per-landmark confidence, joint-angle trace, frame rate, detection rate. Nothing is recorded |
| Dashboard | (signed in) totals, score and flagged share, difficulty history, movement range, repetitions, issue categories, session table, CSV export, filters |
| Session summary | one session in detail, including every repetition and the reasons for the suggestion |
| Research | the project's own evaluation results, with caveats |
| Record data | (research) record landmark numbers of yourself or consenting volunteers; see below |
| Settings & privacy | privacy notice, profile, spoken-feedback default, CSV download, reset level, delete everything |

## Privacy in one paragraph
Pose estimation runs in your browser. Video is not uploaded, not stored, and the camera is switched off when you stop. The backend, running on your own computer, receives only joint-angle numbers. Signed-in users' sessions, repetitions and suggestions are stored in a local database; **Settings & privacy** can download or permanently delete them. No external service is used.

## Manual test protocol for the real webcam (not automated: needs a camera)
Automated tests cannot cover your camera, lighting or body, so run this checklist once on your laptop and note the results:
1. `/analysis`, **Start camera**: permission prompt appears; after allowing, skeleton follows you; note frames/s (aim for 10+) and "person found" (aim for 95%+). Unplug or cover the camera: a clear message appears and nothing crashes.
2. Stand out of view, then step back in: "no person detected" then tracking resumes.
3. `/session`, elbow flexion, level 1, camera: do 6 slow, full repetitions. Expect 5+ counted, "Acceptable" for good ones, a tip per repetition, and a summary after **Stop and save**. Then do 3 very small movements: expect "range short" or "not enough data", never "acceptable".
4. Repeat with squats side-on and with shoulder abduction facing the camera. Note any exercise where counting is off: the illustrative ranges may not match your range (see `docs/limitations-and-safety.md`, "Calibration").
5. Sign in, complete two good real sessions in a row at level 1: the second summary should suggest level 2. Check the Dashboard shows both.
Record what you observe; this is the evidence the live camera path works for your setup.

## Recording your own research data (optional)
1. Open **Record data**. Read the notice, tick consent (for yourself or people who agreed; follow your institution's rules for studies).
2. Enter a participant **code** (for example P01, never a name), the exercise, the side, and what is being done on purpose: correctly, or with a specific error.
3. **Start camera**, then **Record**, do 5 to 10 repetitions, **Stop recording**. Repeat for correct and incorrect takes. Press **Download** for each take. Only landmark numbers and timestamps are saved; no video.
4. Put the files in `datasets/own/` (git-ignored) and run (from `backend`):
   ```powershell
   .\.venv\Scripts\python -m app.ml.cli import-own            # writes datasets\own\reps.csv (take-level labels)
   .\.venv\Scripts\python -m app.ml.cli external --train ..\datasets\external\rehab26\reps.csv --test ..\datasets\own\reps.csv --report ..\datasets\own\report.md
   ```
   This tests a model trained on the public data against recordings from your own camera setup, which is the evidence closest to how the app is really used. Take-level labels assume every repetition in a take was done as intended.
