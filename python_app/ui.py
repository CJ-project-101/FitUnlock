import os
import socket
import subprocess
import sys
import threading
import traceback
import ctypes

from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QVBoxLayout)

sys.path.append(os.path.dirname(__file__))

from exercises import run_squats, run_jumping_jacks, run_push_ups, run_walking, REWARDS
try:
    from exercises import get_last_failure
except ImportError:                      # exercises.py without the liveness check
    def get_last_failure():
        return ""
from session import (add_minutes_to_bank, get_banked_seconds, start_play_session,
                     start_social_session, cancel_social_session, reclaim_stale_social,
                     social_status, init_db)
from auth import update_leaderboard_stats
from leaderboard_ui import LeaderboardWindow
from fx import (BackdropPage, GlowCard, GlowButton, GradientText, IconBadge, FlameLogo, HeatBar,
                ThemeDots, make_divider, set_theme, T, FONT)

MAX_BANK_SECONDS = 3600
BANK_POLL_MS = 1000          # how often the bank display re-reads session.json
GAME_START_GRACE_MS = 3000   # give the game time to appear before we start checking it
GAME_CHECK_MS = 2000         # how often we check whether the game has closed
REELS_WINDOW_TITLE = "Reelz" 
# ── EDIT THESE ──────────────────────────────────────────────────────────
REELS_DIR = Path(r"D:\Major project\reels\client")                           # folder with main.py and qml/
REELS_PYTHON = Path(r"D:\Major project\reels\.venv\Scripts\python.exe")      # python that has PySide6
REELS_SERVER_CMD = None      # to auto-start your server, e.g. [str(REELS_PYTHON), "-m", "uvicorn", "main:app", "--port", "8000"]
REELS_SERVER_DIR = REELS_DIR.parent / "server"


def _port_open(port=8000):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False

def _focus_window_by_title(part):
    """Windows only: bring a visible window whose title contains `part` to the front."""
    if os.name != "nt":
        return False
    user32 = ctypes.windll.user32
    found = []
    Proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def handler(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                if part.lower() in buf.value.lower():
                    found.append(hwnd)
                    return False
        return True

    user32.EnumWindows(Proc(handler), 0)
    if not found:
        return False
    hwnd = found[0]
    user32.ShowWindow(hwnd, 9 if user32.IsIconic(hwnd) else 5)   # restore only if minimized
    user32.SetForegroundWindow(hwnd)
    return True

def fmt(seconds):
    """Formats a number of seconds as m:ss."""
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


class ActivityCard(GlowCard):
    """Clickable exercise card: glowing emoji badge, name, reward and an arrow."""

    def __init__(self, emoji, name, reward_text, color):
        super().__init__(accent=color, clickable=True, radius=14)
        row = QHBoxLayout(self)
        row.setContentsMargins(self.RING + 14, self.RING + 8, self.RING + 18, self.RING + 8)
        row.setSpacing(14)

        badge = IconBadge(emoji, color, 44)
        row.addWidget(badge)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-family: '{FONT}'; font-size: 13pt; font-weight: bold; color: {T.text};")
        reward_lbl = QLabel(reward_text)
        reward_lbl.setStyleSheet(f"font-family: '{FONT}'; font-size: 9pt; color: {T.dim};")
        text_col.addWidget(name_lbl)
        text_col.addWidget(reward_lbl)
        row.addLayout(text_col, 1)

        arrow = QLabel("➜")
        arrow.setStyleSheet(f"font-size: 15pt; font-weight: bold; color: {color};")
        row.addWidget(arrow)

        for w in (badge, name_lbl, reward_lbl, arrow):     # the card itself takes the clicks
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


class FitPlayApp(BackdropPage):
    def __init__(self, shell, on_unlock_callback=None, uid=None, email=None,
                 on_logout=None, is_game_running=None, on_restyle=None):
        super().__init__()
        self.shell = shell                 # the top-level window (hide/show it around exercises)
        self.on_unlock_callback = on_unlock_callback
        self.uid = uid
        self.email = email
        self.on_logout = on_logout
        self.is_game_running = is_game_running
        self.on_restyle = on_restyle       # called after a theme change to rebuild this page
        self._starting_game = False        # blocks double-clicks on Play
        self._waiting_for_game = False
        self._reels_proc = None            # the Reelz client process we launched
        self._leaderboard = None

        self.shell.setWindowTitle("FitPlay")

        init_db()
        reclaim_stale_social()             # return time from an abandoned Reels session
        self.build_ui()

        self._poll_timer = QTimer(self)    # keeps the bank display in sync with session.json
        self._poll_timer.timeout.connect(self._refresh_stats)
        self._poll_timer.start(BANK_POLL_MS)

    # ── small helpers ──────────────────────────────────────────────────────
    def _after(self, ms, fn):
        """One-shot timer that dies with this page."""
        t = QTimer(self)
        t.setSingleShot(True)
        t.timeout.connect(fn)
        t.timeout.connect(t.deleteLater)
        t.start(ms)
        return t

    def _bring_to_front(self):
        fn = getattr(self.shell, "bring_to_front", None)
        if fn is not None:
            fn()
        else:
            self.shell.show()
            self.shell.raise_()
            self.shell.activateWindow()

    def _restore_window(self):
        self.shell.show()
        self.shell.raise_()
        self.shell.activateWindow()

    def _on_theme_selected(self, key):
        set_theme(key)
        if self.on_restyle:
            QTimer.singleShot(0, self.on_restyle)      # rebuild after this click finishes

    # ── UI Layout ──────────────────────────────────────────────────────────
    def build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 10, 34, 14)
        lay.setSpacing(0)

        # Account row: email on the left; theme dots and Log out on the right
        account_row = QHBoxLayout()
        if self.email:
            email_lbl = QLabel(self.email)
            email_lbl.setStyleSheet(f"color: {T.dim}; font-size: 9pt;")
            account_row.addWidget(email_lbl)
        account_row.addStretch(1)
        dots = ThemeDots()
        dots.selected.connect(self._on_theme_selected)
        account_row.addWidget(dots)
        if self.on_logout:
            account_row.addSpacing(8)
            logout_btn = GlowButton("Log out", palette="ghost", height=30, font_px=12)
            logout_btn.clicked.connect(self.do_logout)
            account_row.addWidget(logout_btn)
        lay.addLayout(account_row)

        # Header: logo + title
        header = QHBoxLayout()
        header.setSpacing(4)
        header.addStretch(1)
        header.addWidget(FlameLogo(64, 76))
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.addStretch(1)
        title_col.addWidget(GradientText("FITPLAY", 40, align="left"))
        sub = QLabel("EARN YOUR PLAYTIME WITH REAL MOVEMENT")
        sub.setStyleSheet(f"color: {T.accent_hi}; font-size: 8pt; font-weight: bold; padding-left: 8px;")
        title_col.addWidget(sub)
        title_col.addStretch(1)
        header.addLayout(title_col)
        header.addStretch(1)
        lay.addLayout(header)
        lay.addWidget(make_divider())
        lay.addSpacing(6)

        # ── Stats card ──
        stats = GlowCard(accent=T.accent, radius=16)
        s = QVBoxLayout(stats)
        s.setContentsMargins(stats.RING + 20, stats.RING + 10, stats.RING + 20, stats.RING + 10)
        s.setSpacing(0)
        cap = QLabel("MINUTES AVAILABLE TO PLAY")
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap.setStyleSheet(f"color: {T.accent_hi}; font-size: 9pt; font-weight: bold;")
        s.addWidget(cap)
        self.stats_value = GradientText(fmt(get_banked_seconds()), 46, align="center")
        s.addWidget(self.stats_value)
        self.heat = HeatBar()
        s.addWidget(self.heat)
        self.bank_label = QLabel(f"Banked: {fmt(get_banked_seconds())} / 60:00")
        self.bank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bank_label.setStyleSheet(f"color: {T.dim}; font-size: 9pt; font-weight: bold;")
        s.addWidget(self.bank_label)
        lay.addWidget(stats)

        # ── Activity cards (colors come from the theme) ──
        c_squat, c_jacks, c_push, c_walk = T.activity
        activities = [
            ("🏋", "Squats",
             f"{REWARDS['squats']['reps']} reps  →  {REWARDS['squats']['minutes']} min",
             c_squat, self.do_squats),
            ("⭐", "Jumping Jacks",
             f"{REWARDS['jumping_jacks']['reps']} reps  →  {REWARDS['jumping_jacks']['minutes']} min",
             c_jacks, self.do_jumping_jacks),
            ("💪", "Push-Ups",
             f"{REWARDS['push_ups']['reps']} reps  →  {REWARDS['push_ups']['minutes']} min",
             c_push, self.do_push_ups),
            ("🚶", "Walk", "5 min  →  30 min", c_walk, self.do_walking),
        ]
        for emoji, name, reward, color, handler in activities:
            card = ActivityCard(emoji, name, reward, color)
            card.clicked.connect(handler)
            lay.addWidget(card)

        # ── Buttons: one hero action, one secondary, one quiet ──
        lay.addSpacing(6)
        button_row = QHBoxLayout()
        button_row.setSpacing(2)
        button_row.addStretch(1)
        play_btn = GlowButton("🔥 Play Game", palette="primary", pulse=True, height=46, font_px=15)
        play_btn.clicked.connect(self.do_play_game)
        reels_btn = GlowButton("🎬 Watch Reels", palette="secondary", height=46, font_px=15)
        reels_btn.clicked.connect(self.do_watch_reels)
        board_btn = GlowButton("🏆 Leaderboard", palette="ghost", height=46, font_px=15)
        board_btn.clicked.connect(self.show_leaderboard)
        for b in (play_btn, reels_btn, board_btn):
            button_row.addWidget(b)
        button_row.addStretch(1)
        lay.addLayout(button_row)

        # ── Status bar ──
        lay.addStretch(1)
        self.status_label = QLabel("Pick an activity to get started")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(40)
        self._style_status("info")
        lay.addWidget(self.status_label)

    # ── Activity handlers ─────────────────────────────────────────────────
    def do_squats(self):
        self._run_exercise(run_squats, "squats", REWARDS["squats"]["minutes"])

    def do_jumping_jacks(self):
        self._run_exercise(run_jumping_jacks, "jumping_jacks",
                           REWARDS["jumping_jacks"]["minutes"])

    def do_push_ups(self):
        self._run_exercise(run_push_ups, "push_ups", REWARDS["push_ups"]["minutes"])

    def do_walking(self):
        self._set_status("Opening camera for walking...", "info")

        self.shell.hide()
        try:
            success, minutes_earned = run_walking(target_minutes=5)
        except Exception as e:
            traceback.print_exc()
            self._set_status(f"❌ Walking could not start: {e}", "err")
            return
        finally:
            self._restore_window()

        if success:
            new_total = add_minutes_to_bank(
                minutes_earned, "walking", f"{minutes_earned / 6:.1f} min walked")
            self._sync_leaderboard("walking", minutes_earned)
            self._set_status(
                f"✅ Walked enough! {minutes_earned} min banked. "
                f"Total: {fmt(new_total)}.", "ok")
            self._refresh_stats()
        else:
            self._set_status("❌ Didn't walk long enough. Try again!", "err")

    def _run_exercise(self, exercise_func, activity_name, minutes_reward):
        self._set_status(
            f"Opening camera for {activity_name.replace('_', ' ')}...", "info")

        self.shell.hide()
        try:
            success, reps_done = exercise_func()
        except Exception as e:
            # An error here (e.g. camera or MediaPipe problem) must show in the window,
            # not only in the terminal.
            traceback.print_exc()
            self._set_status(
                f"❌ {activity_name.replace('_', ' ').title()} could not start: {e}", "err")
            return
        finally:
            self._restore_window()      # always bring the window back

        if success:
            new_total = add_minutes_to_bank(minutes_reward, activity_name, reps_done)
            self._sync_leaderboard(activity_name, minutes_reward)
            self._set_status(
                f"✅ Great job! {reps_done} reps done — "
                f"{minutes_reward} min banked. Total: {fmt(new_total)}.", "ok")
            self._refresh_stats()
        else:
            reason = get_last_failure()
            if reason:
                self._set_status(f"❌ {reason}", "err")
            else:
                self._set_status(f"❌ Only completed {reps_done} reps. Try again!", "err")

    # ── Play Game ──────────────────────────────────────────────────────────
    def do_play_game(self):
        if self._starting_game:
            return

        banked_seconds = get_banked_seconds()

        if banked_seconds <= 0:
            self._set_status("No playtime available — complete an exercise first!", "err")
            return

        if not start_play_session(banked_seconds):
            self._set_status("Could not start game session.", "err")
            return

        self._starting_game = True
        self._refresh_stats()
        self._set_status(f"Starting game with {fmt(banked_seconds)}...", "ok")

        if self.on_unlock_callback:
            try:
                self.on_unlock_callback()
            except Exception as e:
                print(f"[ui.py] Launch failed: {e}")
                QMessageBox.critical(self.shell, "Game Launch Error", str(e))
                self._starting_game = False
                return

            if self.is_game_running:
                # Stay alive but out of the way; come back when the game closes.
                self._hide_until_game_closes()
            else:
                self._after(500, QApplication.quit)            # old behaviour
        else:
            print("[ui.py] on_unlock_callback is None - nothing to launch.")
            self._starting_game = False

    # ── Watch Reels ────────────────────────────────────────────────────────
    def do_watch_reels(self):
        if self._starting_game:
            return

        proc = self._reels_proc
        if proc is not None and proc.poll() is None:
            if get_banked_seconds() <= 0:
                self._set_status("Reels is open, but you have no minutes. Complete an exercise first.", "info")
                _focus_window_by_title(REELS_WINDOW_TITLE)
                return
            # New minutes earned: close the old (locked) client so a fresh one claims them.
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, creationflags=flags)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            self._reels_proc = None
            reclaim_stale_social()      # return any unused time from the old session
            self._refresh_stats()

        status = social_status()
        if status == "running":
            self._set_status("A Reels session is already running. Switching to it...", "info")
            _focus_window_by_title(REELS_WINDOW_TITLE)
            return
        if status == "unlocked":
            # time was already granted but the app is not open: just open it again
            self._set_status("Reopening Reels with your granted time...", "ok")
            self._launch_reels_client()
            return

        banked = get_banked_seconds()
        if banked <= 0:
            self._set_status("No playtime available — complete an exercise first!", "err")
            return
        if not (REELS_DIR / "main.py").is_file():
            self._set_status(f"Reels app not found at {REELS_DIR}", "err")
            return
        if not start_social_session(banked, self.email or ""):
            self._set_status("Could not start the reels session.", "err")
            return

        self._refresh_stats()
        self._set_status(f"Opening Reels with {fmt(banked)}...", "ok")

        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        delay = 0
        try:
            if REELS_SERVER_CMD and not _port_open():
                subprocess.Popen(REELS_SERVER_CMD, cwd=str(REELS_SERVER_DIR), creationflags=flags)
                delay = 2500                  # give the server a moment to start
        except OSError as e:
            cancel_social_session()
            self._refresh_stats()
            QMessageBox.critical(self.shell, "Could not start the Reels server", str(e))
            return

        self._after(delay, self._launch_reels_client)

    def _launch_reels_client(self):
        python = REELS_PYTHON if REELS_PYTHON.is_file() else Path(sys.executable)
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            log = open(REELS_DIR / "client.log", "w", encoding="utf-8")   # errors land here
            self._reels_proc = subprocess.Popen(
                [str(python), "main.py"], cwd=str(REELS_DIR),
                stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
        except OSError as e:
            cancel_social_session()           # nothing opened: give the time back
            self._refresh_stats()
            QMessageBox.critical(self.shell, "Could not open Reels", str(e))
            return
        self._after(5000, self._check_reels_started)

    def _check_reels_started(self):
        """If the app died right away (e.g. PySide6 missing), refund the unclaimed time."""
        proc = self._reels_proc
        if proc is not None and proc.poll() is not None:
            if cancel_social_session() > 0:      # >0 only if it was never claimed
                self._refresh_stats()
                self._set_status("❌ Reels failed to start. Time returned. "
                                 "See client.log in the reels\\client folder.", "err")

    # ── Hide while the game runs, return when it closes ───────────────────
    def _hide_until_game_closes(self):
        self._waiting_for_game = True
        self.shell.hide()
        self._after(GAME_START_GRACE_MS, self._check_game_closed)

    def _check_game_closed(self):
        if not self._waiting_for_game:
            return      # we were already brought back (e.g. playtime ran out)
        try:
            still_running = bool(self.is_game_running())
        except Exception as e:
            print(f"[ui.py] Game check failed: {e}")
            still_running = False

        if still_running:
            self._after(GAME_CHECK_MS, self._check_game_closed)
        else:
            print("[ui.py] Game closed - bringing FitPlay back.")
            self.show_again()

    def show_again(self):
        """Brings the window back: the game closed, or another launch asked for it
        (Unity relaunches FitPlay when playtime runs out)."""
        self._starting_game = False
        self._waiting_for_game = False
        self._bring_to_front()
        self._refresh_stats()
        self._set_status("Back in FitPlay. Earn more minutes to play again.", "info")

    # ── Account ────────────────────────────────────────────────────────────
    def do_logout(self):
        if self._starting_game:
            return
        answer = QMessageBox.question(self.shell, "Log out", "Log out of FitPlay on this computer?")
        if answer == QMessageBox.StandardButton.Yes and self.on_logout:
            QTimer.singleShot(0, self.on_logout)    # run after this click finishes

    # ── Leaderboard ────────────────────────────────────────────────────────
    def show_leaderboard(self):
        if self._leaderboard is not None:
            try:
                self._leaderboard.raise_()
                self._leaderboard.activateWindow()
                return
            except RuntimeError:
                self._leaderboard = None       # it was closed
        self._leaderboard = LeaderboardWindow(self.shell, self.uid)
        self._leaderboard.destroyed.connect(lambda *_: setattr(self, "_leaderboard", None))
        self._leaderboard.show()

    def _sync_leaderboard(self, activity_name, minutes):
        """Pushes the result to the cloud in the background. The local bank is the
        source of truth, so a network failure never blocks or undoes banking."""
        if not self.uid:
            return
        threading.Thread(
            target=update_leaderboard_stats,
            args=(self.uid, activity_name, minutes),
            daemon=True,
        ).start()

    # ── Helpers ────────────────────────────────────────────────────────────
    def _style_status(self, kind):
        color = {"info": T.dim, "ok": T.success, "err": T.error}[kind]
        # dark pill so the text stays readable over the backdrop
        self.status_label.setStyleSheet(
            f"background: rgba(4,6,12,175); border-radius: 10px; padding: 8px 14px;"
            f" color: {color}; font-family: '{FONT}'; font-size: 10pt;")

    def _set_status(self, text, kind="info"):
        self._style_status(kind)
        self.status_label.setText(text)
        self.status_label.repaint()

    def _refresh_stats(self):
        banked = get_banked_seconds()
        self.stats_value.setText(fmt(banked))
        self.bank_label.setText(f"Banked: {fmt(banked)} / 60:00")
        self.heat.set_fraction(banked / MAX_BANK_SECONDS)


# ── Run standalone for testing ──────────────────────────────────────────────
if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    from fx import apply_global_style
    apply_global_style()
    window = QMainWindow()
    window.setCentralWidget(FitPlayApp(window))
    window.resize(540, 760)
    window.show()
    sys.exit(qt_app.exec())