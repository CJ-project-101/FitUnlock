# FitPlay

FitPlay is an exercise-gated gaming system. It uses pose detection through a webcam to verify real physical activity, and the earned minutes unlock playtime in a Unity game and in a custom reels (short-video) app.

**Department of Computer Science and Engineering, East West Institute of Technology**
Guide: Sangeeta M R
Team: Calvin K J, Adithya Raj N, Abhishek Yadav, Aditya Mallikarjun

---

## Features

- Real-time pose detection (MediaPipe + OpenCV)
- Four exercises: squats, jumping jacks, push-ups, timed walking
- Liveness check to reduce cheating with replayed exercise videos
- Earned minutes can be banked (up to 1 hour) and used later
- Login, workout history and leaderboard (FastAPI + PostgreSQL)
- Unity game that stays locked until minutes are earned
- Exercise-gated reels app with a content-moderation layer (ReelGuard)
- Local Python-to-Unity bridge using `session.json`, plus SQLite session history

## Architecture

```
Webcam -> Python app (MediaPipe + OpenCV + UI)
              |-- SQLite (local session history)
              |-- session.json  <-->  Unity game
              |-- social_session.json  <-->  Reels app
              `-- FastAPI + PostgreSQL (login, history, leaderboard)

Reels client (PySide6/QML) <--> Reels server (FastAPI, /gate endpoint)
```

## Project structure

```
Major project/
├── python_app/        # FitPlay Python app (main.py, pose_detector.py, exercises.py, session.py, ui.py)
├── reels/
│   ├── server/        # Reels server (FastAPI, run with uvicorn)
│   └── <client>/      # Reels client (PySide6/QML)
├── <game>/            # Unity game build (.exe)
├── requirements.txt
├── setup.bat          # one-time setup
├── FitPlay.vbs        # launcher (hidden windows)
└── README.md
```

## Requirements

- Windows 10/11
- **Python 3.11** (3.11.9 tested). Do not use 3.12+ because MediaPipe is pinned to 0.10.9.
- A working webcam
- Internet connection for first-time setup (package install and model downloads)
- <PostgreSQL / hosted backend details>

## Setup (one time)

1. Install Python 3.11 and tick **Add python.exe to PATH**.
2. Copy the project folder to the laptop. Do not copy the `venv` folder.
3. Double-click `setup.bat`. It creates the virtual environment and installs everything from `requirements.txt`.

Manual setup:

```powershell
cd "<project folder>"
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Running FitPlay

**Easiest:** double-click `FitPlay.vbs`. It starts the reels server, the FitPlay app and (if enabled) the Unity game, all with hidden console windows. Output is saved in `reels\server\server.log` and `python_app\fitplay.log`.

**Manual (for debugging):**

```powershell
# Terminal 1: reels server
cd "<project folder>\reels\server"
..\..\venv\Scripts\activate
uvicorn main:app --port 8000

# Terminal 2: FitPlay app
cd "<project folder>\python_app"
..\venv\Scripts\activate
python main.py
```

**Stopping:** close the apps, then end the background server with `taskkill /f /im python.exe` (this stops all Python processes).

## Troubleshooting

| Problem | Fix |
|---|---|
| App does not start | Open `python_app\fitplay.log` and read the error |
| Reels not loading | Check `reels\server\server.log` and make sure port 8000 is free |
| `ModuleNotFoundError` | Run `setup.bat` again, or `pip install -r requirements.txt` inside the venv |
| MediaPipe install fails | Confirm you are on Python 3.11 (`py -3.11 --version`) |
| Camera not detected | Close other apps using the webcam and check Windows camera privacy settings |
| Reps not counted correctly | Adjust camera distance and angle; thresholds were calibrated on one setup |
| `No module named 'detoxify'` | Only a warning. ReelGuard falls back to rules. Install with `pip install detoxify` for the model |

## Tech stack

Python 3.11, MediaPipe 0.10.9, OpenCV, PySide6 / QML, SQLite, FastAPI, PostgreSQL, Unity (C#)

## License

<Add a license, or "Academic project, all rights reserved.">