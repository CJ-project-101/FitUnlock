@echo off
title FitPlay Launcher
set "ROOT=D:\Major project"
set "PY=%ROOT%\venv\Scripts\python.exe"

echo ==========================================
echo              FITPLAY
echo ==========================================
echo.

echo Starting reels server...
start "Reels Server" /d "%ROOT%\reels\server" cmd /k ""%PY%" -m uvicorn main:app --port 8000"

timeout /t 3 /nobreak >nul

echo Starting FitPlay Python system...
start "FitPlay Python" /d "%ROOT%\python_app" cmd /k ""%PY%" main.py"

timeout /t 3 /nobreak >nul

echo Starting FitPlay Unity game...
REM start "" "D:\path\to\YourGame.exe"

echo.
echo ==========================================
echo           FITPLAY STARTED
echo ==========================================
timeout /t 3 >nul