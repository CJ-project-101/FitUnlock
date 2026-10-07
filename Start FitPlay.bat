@echo off
title FitPlay Launcher

echo ==========================================
echo              FITPLAY
echo ==========================================
echo.
echo Starting FitPlay Python system...
echo.

cd /d "D:\Major project\python_app"
start "" "D:\Major project\venv\Scripts\pythonw.exe" main.py

timeout /t 3 /nobreak >nul

echo.
echo Starting FitPlay Unity game...
echo.

start "" "D:\Major project\unity_build\Platformer_Wellness.exe"

echo.
echo ==========================================
echo       FITPLAY STARTED
echo ==========================================