import tkinter as tk
import subprocess
import os
import sys
import platform

sys.path.append(os.path.dirname(__file__))

from ui import FitPlayApp
from session import lock_session, init_db


# ── Cross-platform path to your Unity build ──────────────────────────────
# Update this after Step 15/16 once your Unity build exists.
# Leave as None for now — the app will just show a message instead of crashing.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # FitPlay/

UNITY_BUILD_PATHS = {
    "Windows": os.path.join(BASE_DIR, "unity_build", "Platformer_Wellness.exe"),
    "Darwin":  os.path.join(BASE_DIR, "unity_build", "FitPlay.app"),
    "Linux":   os.path.join(BASE_DIR, "unity_build", "FitPlay.x86_64"),
}


def get_unity_path():
    """Returns the correct Unity executable path for the current OS."""
    system = platform.system()  # "Windows", "Darwin", or "Linux"
    return UNITY_BUILD_PATHS.get(system)


def launch_game():
    """Launches the Unity build for whichever OS this is running on."""
    game_path = get_unity_path()

    if game_path is None:
        print(f"[main.py] Unsupported OS: {platform.system()}")
        return

    if not os.path.exists(game_path):
        print(f"[main.py] Game not found at: {game_path}")
        print("[main.py] Build your Unity project first (see Step 15).")
        return

    print(f"[main.py] Launching game: {game_path}")

    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen([game_path])
        elif system == "Darwin":
            # .app bundles on macOS need `open`
            subprocess.Popen(["open", game_path])
        elif system == "Linux":
            # Executable bit must be set: chmod +x FitPlay.x86_64
            subprocess.Popen([game_path])
    except Exception as e:
        print(f"[main.py] Failed to launch game: {e}")


def on_app_close(root):
    """Called when the Tkinter window is closed manually."""
    print("[main.py] FitPlay closing. Locking session for safety.")
    lock_session()
    root.destroy()


def main():
    print("=" * 50)
    print("  FitPlay — Starting Up")
    print("=" * 50)

    # 1. Set up database (creates table if first run)
    init_db()

    # 2. Always lock the session on startup —
    #    prevents someone from launching the game using
    #    yesterday's leftover unlocked session.json
    lock_session()

    # 3. Launch the UI, passing launch_game as the callback
    #    that runs after any successful exercise session
    root = tk.Tk()
    app = FitPlayApp(root, on_unlock_callback=launch_game)

    # 4. Make sure closing the window also locks the session
    root.protocol("WM_DELETE_WINDOW", lambda: on_app_close(root))

    root.mainloop()

    print("[main.py] FitPlay closed.")


if __name__ == "__main__":
    main()