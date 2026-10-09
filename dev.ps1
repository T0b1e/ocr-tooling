# Starts backend (8000) and frontend (5173) in two windows. Run from repo root: .\dev.ps1
$root = $PSScriptRoot
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\backend'; & '$root\.venv\Scripts\Activate.ps1'; python -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\frontend'; npm run dev"
Write-Host "Open http://127.0.0.1:5173"
