@echo off
setlocal enabledelayedexpansion
title IVP+AI System Launcher

echo =========================================================================
echo   IVP+AI: Document Understanding and Information Extraction System
echo   NMIMS Implementation Architecture — Layer 1 Production MVP
echo =========================================================================
echo.

:: 1. Locate Python Environment
set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
    echo [INFO] .venv not found. Using system python.
) else (
    echo [INFO] Using virtual environment: %PYTHON_EXE%
)

:: 2. Verify Tesseract OCR
set "TESS_DEFAULT=C:\Program Files\Tesseract-OCR\tesseract.exe"
if not defined TESSERACT_CMD (
    if exist "%TESS_DEFAULT%" (
        set "TESSERACT_CMD=%TESS_DEFAULT%"
        echo [INFO] Detected Tesseract at: !TESSERACT_CMD!
    ) else (
        echo [WARN] Tesseract not found at default path. Ensure it is in PATH or set TESSERACT_CMD.
    )
)

:: 3. Start AI Engine (Port 8001) in a background window
echo [1/3] Starting AI Engine Service on http://127.0.0.1:8001 ...
start "IVP+AI - AI Engine Service (:8001)" "%PYTHON_EXE%" -m uvicorn api:app --app-dir modules/ai-engine --host 127.0.0.1 --port 8001

:: Give AI Engine a moment to bind
timeout /t 2 /nobreak >nul

:: 4. Start Gateway API (Port 8000) in a background window
echo [2/3] Starting Document Processing Gateway on http://127.0.0.1:8000 ...
start "IVP+AI - Gateway API (:8000)" "%PYTHON_EXE%" -m uvicorn api.main:app --host 127.0.0.1 --port 8000

:: Give Gateway a moment to bind
timeout /t 2 /nobreak >nul

:: 5. Open Web Browser
echo [3/3] Opening Web Interface ...
start http://127.0.0.1:8000/

echo.
echo =========================================================================
echo   System running successfully!
echo   - Web Frontend:  http://127.0.0.1:8000/
echo   - Gateway Docs:  http://127.0.0.1:8000/docs
echo   - AI Engine:     http://127.0.0.1:8001/
echo.
echo   Press any key to close this launcher (services will keep running).
echo =========================================================================
pause >nul
