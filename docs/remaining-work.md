# Remaining work (what only you, other people, or hardware can do)

Everything that could be built and checked by software alone is built, tested and documented (`docs/implementation-status.md`). The items below are what is left. Until they are done, the corresponding claims must not be made in the thesis.

## Needs you (no special equipment)
| # | Task | How | Why it matters |
|---|---|---|---|
| 1 | **Webcam check** on your laptop and on a phone | Run the manual checklist in `docs/user-guide.md` ("Manual test protocol for the real webcam"). For the phone, set up local HTTPS (`docs/installation.md`) and use the AR overlay page with the back camera. Write down what you observe (frame rate, "person found" rate, counting accuracy, anything odd). | Nothing has been tested with a real camera yet. This is the evidence that the live path works for a real setup. |
| 2 | **Unity Play-mode check** | In the Unity Editor open `Assets/Scenes/RehabRoom.unity`, press Play, and try the exercise picker, "Live from browser" (web 3D room, Share live pose, room code) and the calibration toggle (`unity-client/README.md`). Note the results in `docs/implementation-status.md`. | These newer Unity features were only tested by automated edit-mode tests, not by hand. |
| 3 | **Own recordings** | Use the **Record data** page for yourself and for consenting volunteers (participant codes, never names; follow your institution's rules), then `python -m app.ml.cli import-own` and the external test (`docs/user-guide.md`, "Recording your own research data"). | The closest evidence to real use: a model trained on public data tested on your own camera setup. Report it even if the result is poor. |
| 4 | **Literature review (Chapter 2)** | Write it from sources you have read and verified, following the outline in `docs/thesis-outline.md` section 2. Verify dataset citations on their Zenodo pages (REHAB26-ViewAngles 23018128, REHAB24-6 13305826). | No citations were invented; `docs/thesis-draft.md` leaves Chapter 2 blank on purpose. |

## Needs outside people or hardware
| # | Task | Notes |
|---|---|---|
| 5 | **Clinician review** of the exercise ranges, the difficulty thresholds and the pain thresholds | The values in `backend/app/exercises/definitions/` and `backend/app/personalization/config.json` are illustrative. A rehabilitation professional must review them before any real use. |
| 6 | **A study with participants** | Ethics approval is needed first. Without a study, nothing can be claimed about adherence or recovery; the adaptive controller has only been tested by unit tests and simulation. |
| 7 | **VR on a headset** | The web "Enter VR" button and the Unity OpenXR packages are built but have never been tried. Steps are in `unity-client/README.md` ("Enabling VR"). The camera-overlay AR page is the supported experience if no headset is available. |

## Optional (not started; not needed for the thesis)
Browser end-to-end tests (Playwright; large browser download), a recurrent-network (LSTM/GRU) baseline compared against the Random Forest (needs PyTorch; unlikely to help with so little data), and a proper internet-facing deployment (certificate from a certificate authority, authentication review, hardening).

## Before you submit
Re-run the evaluation commands if code changed (`docs/research-methodology.md`), report the manual webcam protocol results (or state that it was not done), add page screenshots and the architecture diagram, and keep every claim consistent with `docs/limitations-and-safety.md`.
