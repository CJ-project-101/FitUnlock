import tkinter as tk
import subprocess
import os
import sys
import platform
import socket

sys.path.append(os.path.dirname(__file__))

from ui import FitPlayApp
from session import init_db, lock_active_session

# ─────────────────────────────────────────────────────────────
# GLOBALS
# ─────────────────────────────────────────────────────────────

RESUME_EXISTING_GAME = False
_instance_socket = None
_game_process = None

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── UPDATE THIS ONE LINE once you name your game ──
GAME_EXE_NAME = "Platformer_Wellness"

UNITY_BUILD_PATHS = {
    "Windows": os.path.join(BASE_DIR, "unity_build", f"{GAME_EXE_NAME}.exe"),
    "Darwin": os.path.join(BASE_DIR, "unity_build", f"{GAME_EXE_NAME}.app"),
    "Linux": os.path.join(BASE_DIR, "unity_build", GAME_EXE_NAME),
}


def get_unity_path():
    """Returns the correct Unity executable path for the current OS."""
    return UNITY_BUILD_PATHS.get(platform.system())


# ─────────────────────────────────────────────────────────────
# SINGLE INSTANCE GUARD
# ─────────────────────────────────────────────────────────────

def acquire_single_instance(port=47653):
    """
    Binds a localhost port so only one FitPlay can run at a time.
    The OS releases the port automatically if the process dies.
    """
    global _instance_socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
    except OSError:
        s.close()
        return False
    s.listen(1)
    _instance_socket = s      # keep a reference so it stays bound
    return True


# ─────────────────────────────────────────────────────────────
# CHECK IF UNITY IS ALREADY RUNNING
# ─────────────────────────────────────────────────────────────

def is_game_running():
    """
    Prefers the tracked process handle; falls back to a name-based scan
    if this Python process didn't launch the game itself.
    """
    global _game_process

    if _game_process is not None:
        if _game_process.poll() is None:
            return True
        _game_process = None   # process ended, clear the stale handle

    system = platform.system()
    game_name = f"{GAME_EXE_NAME}.exe" if system == "Windows" else GAME_EXE_NAME

    try:
        if system == "Windows":
            output = subprocess.check_output(
                ["tasklist"], text=True, stderr=subprocess.DEVNULL
            )
            return game_name.lower() in output.lower()
        else:
            output = subprocess.check_output(
                ["pgrep", "-f", game_name], text=True, stderr=subprocess.DEVNULL
            )
            return bool(output.strip())
    except subprocess.CalledProcessError:
        return False


# ─────────────────────────────────────────────────────────────
# BRING EXISTING UNITY WINDOW TO FRONT
# ─────────────────────────────────────────────────────────────

def bring_game_to_front():
    """Windows-only: restores the running game's window, found by PID."""
    if platform.system() != "Windows":
        return

    if _game_process is None:
        print("[main.py] No tracked game process - cannot bring to front.")
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
                return False
            return True

        EnumWindows(EnumWindowsProc(enum_handler), 0)

        if found_hwnd:
            hwnd = found_hwnd[0]
            ctypes.windll.user32.ShowWindow(hwnd, 9)   # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            print("[main.py] Existing Unity game brought to front.")
        else:
            print("[main.py] Game process is running, but its window was not found.")

    except Exception as e:
        print(f"[main.py] Could not bring game to front: {e}")


# ─────────────────────────────────────────────────────────────
# LAUNCH UNITY
# ─────────────────────────────────────────────────────────────

def launch_game():
    global _game_process

    # When Unity itself started this FitPlay, the game is already running
    # and will pick up the new session on its own polling loop.
    if RESUME_EXISTING_GAME:
        print("[main.py] Resume mode - existing Unity instance will detect the session.")
        return

    if is_game_running():
        print("[main.py] Game already running - bringing it to front.")
        bring_game_to_front()
        return

    game_path = get_unity_path()

    if game_path is None:
        print(f"[main.py] Unsupported OS: {platform.system()}")
        return

    if not os.path.exists(game_path):
        print(f"[main.py] Game not found at: {game_path}")
        return

    print(f"[main.py] Launching game: {game_path}")

    system = platform.system()
    try:
        if system == "Darwin":
            _game_process = subprocess.Popen(["open", game_path])
        else:
            _game_process = subprocess.Popen([game_path])
    except Exception as e:
        print(f"[main.py] Failed to launch game: {e}")


# ─────────────────────────────────────────────────────────────
# CLOSE FITPLAY
# ─────────────────────────────────────────────────────────────

def on_app_close(root):
    # Closing FitPlay must NOT touch the bank or the session.
    print("[main.py] FitPlay closing.")
    root.destroy()


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    global RESUME_EXISTING_GAME

    # Must run first so a duplicate copy exits before touching any state.
    if not acquire_single_instance():
        print("[main.py] FitPlay is already running - closing this copy.")
        return

    RESUME_EXISTING_GAME = "--resume-existing" in sys.argv

    print("=" * 50)
    print("  FitPlay - Starting Up")
    print("=" * 50)
    print("[main.py] Started in RESUME mode." if RESUME_EXISTING_GAME
          else "[main.py] Started in NORMAL mode.")

    # 1. Set up database
    init_db()

    # 2. Reset any leftover active play session on a fresh launch.
    #    Never in resume mode, and this must NOT touch banked_seconds.
    if not RESUME_EXISTING_GAME:
        lock_active_session()

    # 3. Start Tkinter application
    root = tk.Tk()

    try:
        app = FitPlayApp(root, on_unlock_callback=launch_game)
    except Exception as e:
        print(f"[main.py] UI ERROR: {e}")
        if sys.stdin is not None:      # pythonw has no console
            input("Press Enter to close...")
        return

    root.protocol("WM_DELETE_WINDOW", lambda: on_app_close(root))

    print("[main.py] Starting Tkinter mainloop...")
    root.mainloop()

    print("[main.py] FitPlay closed.")


if __name__ == "__main__":
    main()