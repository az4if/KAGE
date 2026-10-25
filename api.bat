@echo off
title KAGE — API  (port 8787)
color 0A

echo.
echo  =============================================
echo   KAGE  API  SERVER  —  reanime.py
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

:: ── Node.js  (required by decrypt.mjs) ──────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js not found.  Install Node.js 20+ and add it to PATH.
    pause & exit /b 1
)

:: ── FastAPI / uvicorn ────────────────────────────────────────────────────────
python -c "import fastapi, uvicorn, httpx" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing Python dependencies...
    pip install fastapi "uvicorn[standard]" "httpx[http2]" pycryptodome
    echo.
)

echo  [OK] Dependencies found.
echo.
echo  Starting API on http://localhost:8787 ...
echo  Press Ctrl+C to stop.
echo.

:: ── Launch ───────────────────────────────────────────────────────────────────
cd /d "%~dp0KAGE_API"
python reanime.py

echo.
echo  API stopped.
pause
