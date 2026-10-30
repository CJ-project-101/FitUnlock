@echo off
cd /d "%~dp0"
py -3.11 -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
pause
