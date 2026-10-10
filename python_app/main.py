import tkinter as tk
import subprocess
import os
import sys
import platform

sys.path.append(os.path.dirname(__file__))

from ui import FitPlayApp
from session import init_db


# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── UPDATE THIS ONE LINE once you name your game ──
# Just the filename (without .exe) as it appears in unity_build/
GAME_EXE_NAME = "Platformer_Wellness"   # e.g. change to "MyGameName" later

UNITY_BUILD_PATHS = {
    "Windows": os.path.join(
        BASE_DIR, "unity_build", f"{GAME_EXE_NAME}.exe"
    ),
    "Darwin": os.path.join(
        BASE_DIR, "unity_build", f"{GAME_EXE_NAME}.app"
    ),
    "Linux": os.path.join(
        BASE_DIR, "unity_build", GAME_EXE_NAME
    ),
}

# This will hold the running game's process handle once launched,
# so we don't have to guess window titles at all.
_game_process = None


# ─────────────────────────────────────────────────────────────
# UNITY PATH
# ─────────────────────────────────────────────────────────────

def get_unity_path():
    """Returns the correct Unity executable path for the current OS."""
    system = platform.system()
    return UNITY_BUILD_PATHS.get(system)


# ─────────────────────────────────────────────────────────────
# CHECK IF UNITY IS ALREADY RUNNING
# ─────────────────────────────────────────────────────────────

def is_game_running():
    """
    Checks if the Unity game process is already running.
    Prefers the tracked process handle (_game_process) since that's
    exact and name-independent. Falls back to a name-based scan
    only if this Python process didn't launch it (e.g. restarted mid-session).
    """
    global _game_process

    if _game_process is not None:
        # poll() returns None if still running, exit code otherwise
        if _game_process.poll() is None:
            return True
        else:
            _game_process = None  # process ended, clear the stale handle

    system = platform.system()
    game_name = f"{GAME_EXE_NAME}.exe" if system == "Windows" else GAME_EXE_NAME

    try:
        if system == "Windows":
            output = subprocess.check_output(
                ["tasklist"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            return game_name.lower() in output.lower()
        else:
            output = subprocess.check_output(
                ["pgrep", "-f", game_name],
                text=True,
                stderr=subprocess.DEVNULL
            )
            return bool(output.strip())

    except subprocess.CalledProcessError:
        return False


# ─────────────────────────────────────────────────────────────
# BRING EXISTING UNITY WINDOW TO FRONT
# ─────────────────────────────────────────────────────────────

def bring_game_to_front():
    """
    Windows-only: restores the existing Unity game window,
    found by matching the PID of the process we launched —
    no need to know or guess the window title/game name.
    """

    if platform.system() != "Windows":
        return

    if _game_process is None:
        print("[main.py] No tracked game process — cannot bring to front.")
        return

    try:
        import ctypes
        from ctypes import wintypes

        target_pid = _game_process.pid
        found_hwnd = []

        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
        )
        GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible

        def enum_handler(hwnd, lparam):
            pid = wintypes.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == target_pid and IsWindowVisible(hwnd):
                found_hwnd.append(hwnd)
                return False  # stop enumerating, we found it
            return True

        EnumWindows(EnumWindowsProc(enum_handler), 0)

        if found_hwnd:
            hwnd = found_hwnd[0]
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            print("[main.py] Existing Unity game brought to front.")
        else:
            print(
                "[main.py] Game process is running, "
                "but its window could not be found (still loading?)."
            )

    except Exception as e:
        print(f"[main.py] Could not bring game to front: {e}")


# ─────────────────────────────────────────────────────────────
# LAUNCH UNITY
# ─────────────────────────────────────────────────────────────

def launch_game():
    global _game_process

    # ---------------------------------------------------------
    # If Unity started this Python process while paused,
    # don't launch a second instance — the existing one
    # will detect session.json on its own polling loop.
    # ---------------------------------------------------------

    if RESUME_EXISTING_GAME:
        print("[main.py] Resume mode active.")
        print(
            "[main.py] Existing Unity instance will "
            "detect the unlocked session."
        )
        return

    # ---------------------------------------------------------
    # Normal mode
    # ---------------------------------------------------------

    if is_game_running():
        print(
            "[main.py] Game already running — "
            "bringing existing game to front."
        )
        bring_game_to_front()
        return

    game_path = get_unity_path()

    if game_path is None:
        print(f"[main.py] Unsupported OS: {platform.system()}")
        return

    if not os.path.exists(game_path):
        print(f"[main.py] Game not found at: {game_path}")
        print("[main.py] Build your Unity project first.")
        return

    print(f"[main.py] Launching game: {game_path}")

    system = platform.system()

    try:
        if system == "Windows":
            _game_process = subprocess.Popen([game_path])
        elif system == "Darwin":
            _game_process = subprocess.Popen(["open", game_path])
        elif system == "Linux":
            _game_process = subprocess.Popen([game_path])

    except Exception as e:
        print(f"[main.py] Failed to launch game: {e}")


# ─────────────────────────────────────────────────────────────
# CLOSE FITPLAY
# ─────────────────────────────────────────────────────────────

def on_app_close(root):
    print("[main.py] FitPlay closing.")
    root.destroy()


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    global RESUME_EXISTING_GAME

    RESUME_EXISTING_GAME = "--resume-existing" in sys.argv

    print("=" * 50)
    print("  FitPlay — Starting Up")
    print("=" * 50)

    if RESUME_EXISTING_GAME:
        print("[main.py] Started by Unity in RESUME mode.")
    else:
        print("[main.py] Started in NORMAL mode.")

    # 1. Set up database
    init_db()

    # 2. Lock old session only during normal startup
    
    # 3. Start Tkinter application
    root = tk.Tk()

    try:
        app = FitPlayApp(
            root,
            on_unlock_callback=launch_game
        )
    except Exception as e:
        print(f"[main.py] UI ERROR: {e}")
        input("Press Enter to close...")
        return

    # 4. Lock session when user closes Python app
    root.protocol(
        "WM_DELETE_WINDOW",
        lambda: on_app_close(root)
    )
    print("[main.py] Starting Tkinter mainloop...")
    root.mainloop()

    print("[main.py] FitPlay closed.")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()