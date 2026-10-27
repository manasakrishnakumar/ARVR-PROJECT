# Downloads Google's official MediaPipe pose_landmarker_lite model (a few MB) for local use.
$dest = Join-Path $PSScriptRoot "..\frontend\public\models\pose_landmarker_lite.task"
New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
Invoke-WebRequest "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task" -OutFile $dest
"Saved to $dest"
