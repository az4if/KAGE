@echo off
title KAGE — Frontend  (port 6767)
color 0B

echo.
echo  =============================================
echo   KAGE  FRONTEND  SERVER  —  app.py
echo  =============================================
echo.
echo  Checking dependencies...
echo.

:: ── Python ──────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.  Install Python 3.11+ and add it to PATH.
    pause & exit /b 1
)

:: ── Flask + Requests ─────────────────────────────────────────────────────────
python -c "import flask, requests" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing Python dependencies...
    pip install flask requests
    echo.
)

echo  [OK] Dependencies found.
echo.
echo  Reading API URL from _KEY.txt...
echo.

:: ── Read BASE_API_URL from _KEY.txt for display only ────────────────────────
for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0_KEY.txt") do (
    if /i "%%A"=="BASE_API_URL" (
        set "API_URL=%%B"
    )
)
if defined API_URL (
    echo  API backend  : %API_URL%
) else (
    echo  API backend  : http://localhost:8000  (default)
)

echo  Frontend     : http://localhost:6767
echo.
echo  Open http://localhost:6767 in your browser.
echo  Make sure api.bat is running first!
echo.
echo  Press Ctrl+C to stop.
echo.

:: ── Launch ───────────────────────────────────────────────────────────────────
cd /d "%~dp0"
python app.py

echo.
echo  Frontend stopped.
pause
