import subprocess
import os
import sys
import platform
import socket
import threading

sys.path.append(os.path.dirname(__file__))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from ui import FitPlayApp
from login_ui import LoginScreen
from auth import restore_session, clear_session
from session import init_db, lock_active_session

# ─────────────────────────────────────────────────────────────
# GLOBALS
# ─────────────────────────────────────────────────────────────

RESUME_EXISTING_GAME = False
_instance_socket = None
_game_process = None
_show_requested = threading.Event()        # set when another launch asks us to come forward

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


def start_show_listener():
    """Background thread on the guard socket. When another FitPlay launch connects
    (for example Unity relaunching FitPlay when playtime runs out), it asks this
    instance to come to the front."""
    sock = _instance_socket
    if sock is None:
        return

    def loop():
        while True:
            try:
                conn, _ = sock.accept()
            except OSError:
                return
            try:
                conn.settimeout(1)
                conn.recv(16)
            except OSError:
                pass
            finally:
                conn.close()
            _show_requested.set()

    threading.Thread(target=loop, daemon=True).start()


def ask_running_instance_to_show(port=47653):
    """Called by a duplicate launch just before it exits."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1) as conn:
            conn.sendall(b"show")
    except OSError:
        pass


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
# THE WINDOW  (one top-level window; pages are swapped inside it)
# ─────────────────────────────────────────────────────────────

class Shell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fitplay_app = None
        self.setStyleSheet("QMainWindow { background: #0d0d1a; }")
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

    def set_page(self, widget, mode):
        """mode is 'login' (fixed small window) or 'main' (fixed width, resizable height)."""
        while self._stack.count():
            old = self._stack.widget(0)
            self._stack.removeWidget(old)
            old.deleteLater()
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

        if mode == "login":
            self._login_geometry()
        else:
            self._main_geometry()
        self.show()
        self.raise_()
        self.activateWindow()

    def _login_geometry(self):
        area = QGuiApplication.primaryScreen().availableGeometry()
        w, h = 480, min(640, area.height() - 80)
        self.setFixedSize(w, h)
        self.move(area.x() + (area.width() - w) // 2,
                  max(area.y() + (area.height() - h) // 2 - 20, area.y()))

    def _main_geometry(self):
        area = QGuiApplication.primaryScreen().availableGeometry()
        h = min(760, area.height() - 40)
        self.setMinimumSize(540, min(640, h))
        self.setMaximumSize(540, 16777215)      # width fixed, height resizable (like before)
        self.resize(540, h)

    def bring_to_front(self):
        """Windows can refuse to focus a window from a background process, so flip
        always-on-top briefly to force it forward."""
        self.show()
        self.raise_()
        self.activateWindow()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.show()
        QTimer.singleShot(300, self._drop_topmost)

    def _drop_topmost(self):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.show()

    def closeEvent(self, event):
        on_app_close(self)
        event.accept()


# ─────────────────────────────────────────────────────────────
# CLOSE FITPLAY
# ─────────────────────────────────────────────────────────────

def on_app_close(shell):
    # Closing FitPlay must NOT touch the bank or the session.
    # (It also keeps the saved login, so the next launch skips the login screen.)
    print("[main.py] FitPlay closing.")
    QApplication.quit()


# ─────────────────────────────────────────────────────────────
# COME BACK TO THE FRONT
# ─────────────────────────────────────────────────────────────

def bring_fitplay_forward(shell):
    """Shows the FitPlay window again (it hides itself while the game runs)."""
    app = shell.fitplay_app
    try:
        if app is not None:
            app.show_again()
        else:
            shell.bring_to_front()
    except RuntimeError:
        pass      # the page was just replaced


def poll_show_requests(shell):
    """Runs on the GUI thread; checks whether another launch asked us to come forward."""
    if _show_requested.is_set():
        _show_requested.clear()
        print("[main.py] Another launch asked FitPlay to come forward.")
        bring_fitplay_forward(shell)


# ─────────────────────────────────────────────────────────────
# LOGIN / LOGOUT FLOW
# ─────────────────────────────────────────────────────────────

def start_app(shell, uid, email):
    """Swaps whatever is on screen for the main FitPlay UI. Returns True on success."""
    try:
        app = FitPlayApp(shell, on_unlock_callback=launch_game, uid=uid, email=email,
                         on_logout=lambda: do_logout(shell),
                         is_game_running=is_game_running,
                         on_restyle=lambda: start_app(shell, uid, email))
    except Exception as e:
        print(f"[main.py] UI ERROR: {e}")
        if sys.stdin is not None:      # pythonw has no console
            input("Press Enter to close...")
        return False

    shell.fitplay_app = app            # keep a reference alive for the whole session
    shell.set_page(app, "main")
    return True


def _on_login_success(shell, uid, email):
    if not start_app(shell, uid, email):
        QApplication.quit()


def show_login(shell):
    """Shows the login screen. Returns True on success."""
    try:
        page = LoginScreen(shell,
                           on_login_success=lambda uid, email: _on_login_success(shell, uid, email),
                           on_restyle=lambda: show_login(shell))
    except Exception as e:
        print(f"[main.py] LOGIN ERROR: {e}")
        if sys.stdin is not None:      # pythonw has no console
            input("Press Enter to close...")
        return False

    shell.fitplay_app = None
    shell.set_page(page, "login")
    return True


def do_logout(shell):
    """Forgets the saved login and returns to the login screen.
    Does NOT touch the local bank or the play session."""
    print("[main.py] Logging out.")
    clear_session()
    if not show_login(shell):
        QApplication.quit()


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    global RESUME_EXISTING_GAME

    # Must run first so a duplicate copy exits before touching any state.
    if not acquire_single_instance():
        print("[main.py] FitPlay is already running - asking it to come forward.")
        ask_running_instance_to_show()
        return

    start_show_listener()

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

    # 3. Start the Qt application
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("FitPlay")
    qt_app.setStyle("Fusion")
    # The window is hidden while exercises/the game run, so we quit explicitly
    # (Shell.closeEvent) instead of "when the last window closes".
    from fx import apply_global_style
    apply_global_style()          # dark message boxes, tooltips and scrollbars in the theme
    qt_app.setQuitOnLastWindowClosed(False)

    shell = Shell()

    show_timer = QTimer(shell)
    show_timer.timeout.connect(lambda: poll_show_requests(shell))
    show_timer.start(500)

    # Skip the login screen when a saved login is still valid (window not shown yet)
    try:
        saved = restore_session()
    except Exception as e:
        print(f"[main.py] Could not restore saved login: {e}")
        saved = None

    if saved:
        print("[main.py] Saved login found - skipping login screen.")
        started = start_app(shell, saved[0], saved[1])
    else:
        started = show_login(shell)

    if not started:
        return

    print("[main.py] Starting Qt event loop...")
    qt_app.exec()

    print("[main.py] FitPlay closed.")


if __name__ == "__main__":
    main()