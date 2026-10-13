import os
import sys
import tkinter as tk

sys.path.append(os.path.dirname(__file__))
from auth import get_leaderboard

BG_DARK = "#0d0d1a"
BG_CARD = "#16162b"
TEXT_MAIN = "#f2f2f7"
TEXT_DIM = "#8a8a9e"
TEAL = "#0fd8a8"
GOLD, SILVER, BRONZE = "#ffd700", "#c0c0c0", "#cd7f32"


class LeaderboardWindow:
    def __init__(self, parent, current_uid=None):
        self.current_uid = current_uid
        self.window = tk.Toplevel(parent)
        self.window.title("FitPlay — Leaderboard")
        self.window.geometry("420x640")
        self.window.configure(bg=BG_DARK)

        tk.Label(self.window, text="🏆 LEADERBOARD", font=("Segoe UI", 20, "bold"),
                 bg=BG_DARK, fg=TEXT_MAIN).pack(pady=(20, 10))
        tk.Button(self.window, text="⟳ Refresh", command=self.refresh, bd=0,
                  bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 10),
                  cursor="hand2", padx=12, pady=4).pack(pady=(0, 10))

        self.list_frame = tk.Frame(self.window, bg=BG_DARK)
        self.list_frame.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        entries = get_leaderboard(limit=10)
        if not entries:
            tk.Label(self.list_frame, text="No data yet — be the first!",
                     font=("Segoe UI", 12), bg=BG_DARK, fg=TEXT_DIM).pack(pady=40)
            return
        for rank, entry in enumerate(entries, start=1):
            self._make_row(rank, entry)

    def _make_row(self, rank, entry):
        color = GOLD if rank == 1 else SILVER if rank == 2 else BRONZE if rank == 3 else TEXT_DIM
        is_me = entry["uid"] == self.current_uid

        row = tk.Frame(self.list_frame, bg=BG_CARD,
                       highlightthickness=2 if is_me else 0, highlightbackground=TEAL)
        row.pack(fill="x", padx=20, pady=4)

        tk.Label(row, text=f"#{rank}", font=("Segoe UI", 14, "bold"),
                 bg=BG_CARD, fg=color, width=4).pack(side="left", padx=10, pady=10)

        info = tk.Frame(row, bg=BG_CARD)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=entry["name"] + ("  (you)" if is_me else ""),
                 font=("Segoe UI", 12, "bold"), bg=BG_CARD, fg=TEXT_MAIN,
                 anchor="w").pack(fill="x")
        tk.Label(info, text=f"{entry['sessions']} sessions", font=("Segoe UI", 9),
                 bg=BG_CARD, fg=TEXT_DIM, anchor="w").pack(fill="x")

        tk.Label(row, text=f"{entry['minutes']} min", font=("Segoe UI", 12, "bold"),
                 bg=BG_CARD, fg=TEAL).pack(side="right", padx=15)