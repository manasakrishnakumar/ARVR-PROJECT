# One-command setup for Windows PowerShell (run from the repository root): .\scripts\setup.ps1
# Creates the backend virtual environment, installs backend and frontend packages, copies the MediaPipe WASM runtime
# into the frontend (served locally), and downloads Google's pose model (about 6 MB) unless it is already present.
# Native tools (pip, npm) print harmless notices on stderr, so success is judged by exit code, not by stderr output.
$root = Split-Path $PSScriptRoot -Parent

function Step([string]$what, [scriptblock]$cmd) {
  & $cmd
  if ($LASTEXITCODE -ne 0) { throw "Failed: $what (exit code $LASTEXITCODE)" }
}

foreach ($tool in "python", "node", "npm") {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool was not found. Install it (see docs/installation.md) and open a new terminal." }
}
if ($root.Length -gt 120) { Write-Warning "The project path is long; pip may fail on Windows. Consider a shorter folder." }

Write-Host "== Backend =="
Push-Location (Join-Path $root "backend")
try {
  if (-not (Test-Path ".venv")) { Step "create virtual environment" { python -m venv .venv } }
  Step "install backend packages" { .\.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt 2>&1 | Out-Null; $global:LASTEXITCODE = $LASTEXITCODE }
} finally { Pop-Location }

Write-Host "== Frontend =="
Push-Location (Join-Path $root "frontend")
try {
  Step "npm install" { npm install 2>&1 | Out-Null; $global:LASTEXITCODE = $LASTEXITCODE }
  New-Item -ItemType Directory -Force "public\wasm" | Out-Null
  Copy-Item "node_modules\@mediapipe\tasks-vision\wasm\*" "public\wasm\" -Force
} finally { Pop-Location }

Write-Host "== Pose model =="
$model = Join-Path $root "frontend\public\models\pose_landmarker_lite.task"
if (Test-Path $model) { Write-Host "Already present: $model" } else { & (Join-Path $PSScriptRoot "download_pose_model.ps1") }

Write-Host "`nDone. Start the backend:  cd backend; .\.venv\Scripts\python -m uvicorn app.main:app --reload"
Write-Host "Start the frontend:       cd frontend; npm run dev -- --host 127.0.0.1   (then open http://127.0.0.1:5173)"
