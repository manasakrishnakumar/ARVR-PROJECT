# Unity client (optional)

A Unity 6 (6000.6.7f1) desktop client for the ARVR backend: a 3D room, a virtual trainer, an avatar for you, and a live HUD. It uses the **same backend and exercise data** as the web app, so counting, quality assessment, calibration and the adaptive suggestion are identical. No headset is needed.

Research prototype, not a medical device.

## What it does
- **All exercises**: the list comes from `GET /api/exercises` (falls back to elbow flexion if the backend is down). A virtual trainer (amber) loops the illustrative movement; you (teal) are the second figure.
- **Three angle sources**
  - *Trainer demo*: a synthetic sweep, sent to the backend as a **demo session** (never saved to a history).
  - *Manual slider*: you set the movement.
  - *Live from browser*: the web app's **3D room** page publishes your real webcam pose (numbers only, no video) to a room code on the local backend; Unity joins that room and mirrors you. Pose estimation and counting stay in the browser.
- **Calibration** ("Calibrate to my range", on by default): the backend measures the range you actually move in during the first seconds and counts relative to it; no repetitions are lost.
- After **Stop and save**: the adaptive suggestion with reasons and the safety note.
- The room keeps running if the backend is unreachable, and says so.

## What it does not do
- No pose estimation inside Unity (that would need a plugin such as MediaPipe for Unity): real pose comes through the browser relay.
- No accounts or charts (use the web app).
- **VR is prepared but NOT tested**: the OpenXR packages are installed and the HUD reports XR status, but XR is switched off and no headset has been used. See *Enabling VR* below.

## Run it
1. Install Unity Hub and Editor **6000.6.7f1**; sign in and activate the free Personal licence in the Hub.
2. Open the `unity-client` folder as a project (Hub: Add > Add project from disk). If Hub does not accept it, open it from a terminal: `"C:\Program Files\Unity\Hub\Editor\6000.6.7f1\Editor\Unity.exe" -projectPath "<path to unity-client>"`.
3. Open `Assets/Scenes/RehabRoom.unity` (menu **ARVR > Create room scene** rebuilds it).
4. Start the backend (`docs/installation.md`), press **Play**, pick an exercise and a source, click **Start**.
5. For *Live from browser*: in the web app open **3D room**, tick **Share live pose**, start the camera there, then type the room code in Unity and click **Start**.

## Enabling VR (untested: no headset was available)
The project includes `com.unity.xr.management` and `com.unity.xr.openxr`. To try a headset: Edit > Project Settings > XR Plug-in Management > Windows tab > tick **OpenXR**, add your headset's interaction profile under OpenXR, start the headset's OpenXR runtime (for example SteamVR or the Meta/Windows Mixed Reality app), then press Play. The HUD line shows `XR device active` when it works. The room currently uses a fixed camera, so a proper XR rig (head-tracked camera, hand controllers for the Start button) still has to be added and tested on real hardware; the IMGUI buttons are desktop-only.

## Tests and builds (batch mode, no window needed; close the Editor first)
```powershell
$u = "C:\Program Files\Unity\Hub\Editor\6000.6.7f1\Editor\Unity.exe"; $p = "<path to unity-client>"
& $u -batchmode -nographics -projectPath $p -runTests -testPlatform EditMode -testResults tests.xml -logFile tests.log
& $u -batchmode -nographics -projectPath $p -executeMethod Arvr.EditorTools.BuildScript.BuildWindows -quit -logFile build.log   # Builds/Windows/ARVR-Unity.exe (git-ignored)
```
Edit-mode tests (`Assets/Tests/EditMode`) cover the pose maths, trainer poses for four joint types on both sides, message and URL parsing, and the relay frame format.

## Verification status
See `docs/implementation-status.md` (Unity section) for what was verified and when; anything not listed there is untested.
