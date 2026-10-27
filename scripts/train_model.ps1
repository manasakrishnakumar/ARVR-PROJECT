# Reproducible ML run: generate the SYNTHETIC sample dataset (optional) and train + evaluate.
# Usage:  .\scripts\train_model.ps1                       (synthetic sample data)
#         .\scripts\train_model.ps1 -Data path\to\real.csv (your own labelled repetition CSV)
param([string]$Data = "", [int]$Participants = 30, [int]$Seed = 0)
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
Push-Location (Join-Path $root "backend")
try {
  if ($Data -eq "") {
    & $py -m app.ml.cli generate --participants $Participants --seed $Seed
    $Data = Join-Path $root "datasets\sample\synthetic_reps.csv"
  }
  & $py -m app.ml.cli train --data $Data --seed $Seed
} finally { Pop-Location }
