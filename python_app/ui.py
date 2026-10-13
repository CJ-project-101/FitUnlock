import tkinter as tk
from tkinter import messagebox
import sys
import os
import threading
import traceback                                              # NEW

sys.path.append(os.path.dirname(__file__))

from exercises import run_squats, run_jumping_jacks, run_push_ups, run_walking, REWARDS
from session import add_minutes_to_bank, get_banked_seconds, start_play_session, init_db
from auth import update_leaderboard_stats
from leaderboard_ui import LeaderboardWindow


# ── Color palette ──────────────────────────────────────────────────────────
BG_DARK         = "#0d0d1a"
BG_CARD         = "#16162b"
ACCENT_PINK     = "#e94560"
ACCENT_PINK_H   = "#ff5e7a"
ACCENT_BLUE     = "#3f8cff"
ACCENT_BLUE_H   = "#5fa3ff"
ACCENT_PURPLE   = "#8c52ff"
ACCENT_PURPLE_H = "#a06fff"
ACCENT_TEAL     = "#0fd8a8"
ACCENT_TEAL_H   = "#2be8bc"
TEXT_MAIN       = "#f2f2f7"
TEXT_DIM        = "#8a8a9e"
SUCCESS         = "#0fd8a8"
ERROR           = "#ff5e7a"

BANK_POLL_MS = 1000    # how often the bank display re-reads session.json


def fmt(seconds):
    """Formats a number of seconds as m:ss."""
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


class FitPlayApp:
    def __init__(self, root, on_unlock_callback=None, uid=None, email=None,
                 on_logout=None):                              # CHANGED
        self.root = root
        self.on_unlock_callback = on_unlock_callback
        self.uid = uid
        self.email = email
        self.on_logout = on_logout                             # NEW
        self._starting_game = False     # blocks double-clicks on Play

        self.root.title("FitPlay")
        self.root.geometry("540x760")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, True)

        init_db()
        self.build_ui()
        self._poll_bank()

    # ── UI Layout ──────────────────────────────────────────────────────────
    def build_ui(self):
        # ── Header ──
        header = tk.Frame(self.root, bg=BG_DARK)
        header.pack(fill="x", pady=(14, 0))                    # CHANGED (was 36) to make room for the account row

        # NEW: account row — signed-in email on the left, Log out on the right
        account_row = tk.Frame(header, bg=BG_DARK)
        account_row.pack(fill="x", padx=40)

        if self.email:
            tk.Label(account_row, text=self.email, font=("Segoe UI", 9),
                     bg=BG_DARK, fg=TEXT_DIM).pack(side="left")

        if self.on_logout:
            tk.Button(account_row, text="Log out", font=("Segoe UI", 9, "bold"),
                      bg=BG_CARD, fg=TEXT_MAIN, bd=0, padx=10, pady=3,
                      cursor="hand2", command=self.do_logout).pack(side="right")

        tk.Label(header, text="EARN YOUR PLAYTIME WITH REAL MOVEMENT",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_DARK, fg=ACCENT_PINK).pack(pady=(14, 0))   # CHANGED (was 4)

        # ── Stats card ──
        stats_card = tk.Frame(self.root, bg=BG_CARD, highlightthickness=1,
                              highlightbackground="#2a2a45")
        stats_card.pack(fill="x", padx=40, pady=(24, 20))

        inner = tk.Frame(stats_card, bg=BG_CARD)
        inner.pack(pady=16)

        tk.Label(inner, text="MINUTES AVAILABLE TO PLAY",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_CARD, fg=TEXT_DIM).pack()

        self.stats_value_label = tk.Label(
            inner, text=fmt(get_banked_seconds()),
            font=("Segoe UI", 34, "bold"),
            bg=BG_CARD, fg=ACCENT_TEAL)
        self.stats_value_label.pack()

        # ── Activity buttons ──
        activities_frame = tk.Frame(self.root, bg=BG_DARK)
        activities_frame.pack(fill="x", padx=40)

        self._make_activity_card(
            activities_frame, "🏋", "Squats",
            f"{REWARDS['squats']['reps']} reps  →  {REWARDS['squats']['minutes']} min",
            ACCENT_PINK, ACCENT_PINK_H, self.do_squats)

        self._make_activity_card(
            activities_frame, "⭐", "Jumping Jacks",
            f"{REWARDS['jumping_jacks']['reps']} reps  →  {REWARDS['jumping_jacks']['minutes']} min",
            ACCENT_BLUE, ACCENT_BLUE_H, self.do_jumping_jacks)

        self._make_activity_card(
            activities_frame, "💪", "Push-Ups",
            f"{REWARDS['push_ups']['reps']} reps  →  {REWARDS['push_ups']['minutes']} min",
            ACCENT_PURPLE, ACCENT_PURPLE_H, self.do_push_ups)

        self._make_activity_card(
            activities_frame, "🚶", "Walk",
            "5 min  →  30 min",
            ACCENT_TEAL, ACCENT_TEAL_H, self.do_walking)

        # ── Bank + Play ──
        self.bank_label = tk.Label(
            self.root, text=f"Banked: {fmt(get_banked_seconds())} / 60:00",
            font=("Segoe UI", 14, "bold"), bg=BG_DARK, fg=ACCENT_TEAL)
        self.bank_label.pack(pady=10)

        # Play and Leaderboard share one row so the window height is unchanged
        button_row = tk.Frame(self.root, bg=BG_DARK)
        button_row.pack(pady=10)

        tk.Button(
            button_row, text="▶ Play Game",
            bg=ACCENT_TEAL, fg="white",
            font=("Segoe UI", 13, "bold"),
            command=self.do_play_game, cursor="hand2"
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_row, text="🏆 Leaderboard",
            bg=BG_CARD, fg=TEXT_MAIN,
            font=("Segoe UI", 13, "bold"),
            command=self.show_leaderboard, cursor="hand2"
        ).pack(side="left")

        # ── Status bar ──
        self.status_label = tk.Label(
            self.root, text="Pick an activity to get started",
            font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT_DIM, wraplength=460)
        self.status_label.pack(pady=(10, 24))

    def _make_activity_card(self, parent, emoji, name, reward_text,
                            color, hover_color, command):
        card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1,
                        highlightbackground="#2a2a45", cursor="hand2")
        card.pack(fill="x", pady=6)

        content = tk.Frame(card, bg=BG_CARD, cursor="hand2")
        content.pack(fill="x", padx=18, pady=14)

        left = tk.Frame(content, bg=BG_CARD, cursor="hand2")
        left.pack(side="left")

        tk.Label(left, text=emoji, font=("Segoe UI", 22),
                 bg=BG_CARD, fg=color, cursor="hand2").pack(side="left", padx=(0, 14))

        text_col = tk.Frame(left, bg=BG_CARD, cursor="hand2")
        text_col.pack(side="left")

        tk.Label(text_col, text=name, font=("Segoe UI", 13, "bold"),
                 bg=BG_CARD, fg=TEXT_MAIN, cursor="hand2", anchor="w").pack(anchor="w")
        tk.Label(text_col, text=reward_text, font=("Segoe UI", 9),
                 bg=BG_CARD, fg=TEXT_DIM, cursor="hand2", anchor="w").pack(anchor="w")

        arrow = tk.Label(content, text="→", font=("Segoe UI", 16, "bold"),
                         bg=BG_CARD, fg=color, cursor="hand2")
        arrow.pack(side="right")

        widgets = [card, content, left, text_col, arrow] + list(text_col.winfo_children())

        def on_enter(e):
            card.configure(highlightbackground=color)
            arrow.configure(fg=hover_color)

        def on_leave(e):
            card.configure(highlightbackground="#2a2a45")
            arrow.configure(fg=color)

        for w in widgets:
            w.bind("<Button-1>", lambda e: command())
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    # ── Activity handlers ─────────────────────────────────────────────────
    def do_squats(self):
        self._run_exercise(run_squats, "squats", REWARDS["squats"]["minutes"])

    def do_jumping_jacks(self):
        self._run_exercise(run_jumping_jacks, "jumping_jacks",
                           REWARDS["jumping_jacks"]["minutes"])

    def do_push_ups(self):
        self._run_exercise(run_push_ups, "push_ups", REWARDS["push_ups"]["minutes"])

    def do_walking(self):
        self._set_status("Opening camera for walking...", TEXT_DIM)

        self.root.withdraw()
        try:
            success, minutes_earned = run_walking(target_minutes=5)
        except Exception as e:                                          # NEW
            traceback.print_exc()
            self._set_status(f"❌ Walking could not start: {e}", ERROR)
            return
        finally:
            self.root.deiconify()

        if success:
            new_total = add_minutes_to_bank(
                minutes_earned, "walking", f"{minutes_earned / 6:.1f} min walked")
            self._sync_leaderboard("walking", minutes_earned)
            self._set_status(
                f"✅ Walked enough! {minutes_earned} min banked. "
                f"Total: {fmt(new_total)}.", SUCCESS)
            self._refresh_stats()
        else:
            self._set_status("❌ Didn't walk long enough. Try again!", ERROR)

    def _run_exercise(self, exercise_func, activity_name, minutes_reward):
        self._set_status(
            f"Opening camera for {activity_name.replace('_', ' ')}...", TEXT_DIM)

        self.root.withdraw()
        try:
            success, reps_done = exercise_func()
        except Exception as e:                                          # NEW
            # Previously an error here (e.g. camera or MediaPipe problem) only
            # appeared in the terminal and the button seemed to do nothing.
            traceback.print_exc()
            self._set_status(
                f"❌ {activity_name.replace('_', ' ').title()} could not start: {e}", ERROR)
            return
        finally:
            self.root.deiconify()      # always bring the window back

        if success:
            new_total = add_minutes_to_bank(minutes_reward, activity_name, reps_done)
            self._sync_leaderboard(activity_name, minutes_reward)
            self._set_status(
                f"✅ Great job! {reps_done} reps done — "
                f"{minutes_reward} min banked. Total: {fmt(new_total)}.", SUCCESS)
            self._refresh_stats()
        else:
            self._set_status(f"❌ Only completed {reps_done} reps. Try again!", ERROR)

    # ── Play Game ──────────────────────────────────────────────────────────
    def do_play_game(self):
        if self._starting_game:
            return

        banked_seconds = get_banked_seconds()

        if banked_seconds <= 0:
            self._set_status("No playtime available — complete an exercise first!", ERROR)
            return

        if not start_play_session(banked_seconds):
            self._set_status("Could not start game session.", ERROR)
            return

        self._starting_game = True
        self._refresh_stats()
        self._set_status(f"Starting game with {fmt(banked_seconds)}...", SUCCESS)

        if self.on_unlock_callback:
            try:
                self.on_unlock_callback()
            except Exception as e:
                print(f"[ui.py] Launch failed: {e}")
                messagebox.showerror("Game Launch Error", str(e))
                self._starting_game = False
                return

            self.root.after(500, self.root.destroy)
        else:
            print("[ui.py] on_unlock_callback is None - nothing to launch.")
            self._starting_game = False

    # ── Account (NEW) ──────────────────────────────────────────────────────
    def do_logout(self):
        if self._starting_game:
            return
        if messagebox.askyesno("Log out", "Log out of FitPlay on this computer?"):
            if self.on_logout:
                self.root.after(0, self.on_logout)    # run after this click finishes

    # ── Leaderboard ────────────────────────────────────────────────────────
    def show_leaderboard(self):
        LeaderboardWindow(self.root, self.uid)

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
    def _set_status(self, text, color):
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()

    def _refresh_stats(self):
        banked = get_banked_seconds()
        self.stats_value_label.config(text=fmt(banked))
        self.bank_label.config(text=f"Banked: {fmt(banked)} / 60:00")
        self.root.update_idletasks()

    def _poll_bank(self):
        """Keeps the display in sync when Unity returns unused time."""
        try:
            self._refresh_stats()
            self.root.after(BANK_POLL_MS, self._poll_bank)
        except tk.TclError:
            pass      # window was closed


# ── Run standalone for testing ──────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = FitPlayApp(root)
    root.mainloop()