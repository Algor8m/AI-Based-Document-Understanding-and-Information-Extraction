# IVP+AI — Windows PowerShell Launch Script
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  IVP+AI: Document Understanding and Information Extraction System" -ForegroundColor White
Write-Host "  NMIMS Implementation Architecture — Layer 1 Production MVP" -ForegroundColor Yellow
Write-Host "=========================================================================" -ForegroundColor Cyan

$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
    Write-Host "[INFO] .venv not found. Using system python." -ForegroundColor Gray
} else {
    Write-Host "[INFO] Using virtual environment: $PythonExe" -ForegroundColor Green
}

$TessPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (-not $env:TESSERACT_CMD) {
    if (Test-Path $TessPath) {
        $env:TESSERACT_CMD = $TessPath
        Write-Host "[INFO] Detected Tesseract at: $TessPath" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Tesseract not found at default location. Ensure it is in PATH." -ForegroundColor Yellow
    }
}

Write-Host "`n[1/3] Launching AI Engine Service on port 8001..." -ForegroundColor Cyan
Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn api:app --app-dir modules/ai-engine --host 127.0.0.1 --port 8001" -WindowStyle Minimized

Start-Sleep -Seconds 2

Write-Host "[2/3] Launching Document Processing Gateway on port 8000..." -ForegroundColor Cyan
Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn api.main:app --host 127.0.0.1 --port 8000" -WindowStyle Minimized

Start-Sleep -Seconds 2

Write-Host "[3/3] Opening Web Interface in default browser..." -ForegroundColor Cyan
Start-Process "http://127.0.0.1:8000/"

Write-Host "`nSystem operational!" -ForegroundColor Green
Write-Host "  Frontend:     http://127.0.0.1:8000/" -ForegroundColor White
Write-Host "  API Docs:     http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  AI Engine:    http://127.0.0.1:8001/" -ForegroundColor White
