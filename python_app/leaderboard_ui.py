import os
import sys

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QRadialGradient
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QScrollArea,
                               QVBoxLayout, QWidget)

sys.path.append(os.path.dirname(__file__))
from auth import get_leaderboard
from qtutil import run_async
from fx import BackdropPage, GlowCard, GlowButton, GradientText, make_divider, T, FONT

GOLD, SILVER, BRONZE = "#ffd34d", "#d6dde6", "#d9823b"
TOP_STYLE = {                       # highlight, shadow, glow
    1: ("#fff6c2", "#e0a800", GOLD),
    2: ("#ffffff", "#9aa3ad", SILVER),
    3: ("#ffd2a3", "#b0602a", BRONZE),
}


class RankBadge(QWidget):
    """Round medal: gold, silver, bronze for the top three, a plain ring after that."""

    def __init__(self, rank):
        super().__init__()
        self._rank = rank
        self.setFixedSize(40, 40)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self.width() / 2 - 2
        top = TOP_STYLE.get(self._rank)
        p.setPen(Qt.PenStyle.NoPen)
        if top:
            hi, lo, _glow = top
            g = QRadialGradient(QPointF(c.x() - r * 0.3, c.y() - r * 0.35), r * 1.5)
            g.setColorAt(0.0, QColor(hi))
            g.setColorAt(1.0, QColor(lo))
            p.setBrush(QBrush(g))
            p.drawEllipse(c, r, r)
            text_color = QColor("#2a1400")
        else:
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawEllipse(c, r, r)
            text_color = QColor(T.dim)
        f = QFont(FONT)
        f.setPixelSize(16)
        f.setBold(True)
        p.setFont(f)
        p.setPen(text_color)
        p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, str(self._rank))


class LeaderboardWindow(QDialog):
    def __init__(self, parent=None, current_uid=None):
        super().__init__(parent)
        self.current_uid = current_uid
        self._loading = False

        self.setWindowTitle("FitPlay — Leaderboard")
        self.resize(420, 660)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.page = BackdropPage()
        outer.addWidget(self.page)

        root = QVBoxLayout(self.page)
        root.setContentsMargins(0, 16, 0, 12)
        root.setSpacing(0)

        root.addWidget(GradientText("LEADERBOARD", 32, align="center"))
        sub = QLabel("THE HOTTEST MOVERS")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {T.accent_hi}; font-size: 9pt; font-weight: bold;")
        root.addWidget(sub)
        root.addSpacing(8)
        div_row = QHBoxLayout()
        div_row.setContentsMargins(30, 0, 30, 0)
        div_row.addWidget(make_divider())
        root.addLayout(div_row)
        root.addSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.refresh_btn = GlowButton("⟳ Refresh", palette="ghost", height=34, font_px=13)
        self.refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)
        root.addSpacing(4)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll.viewport().setStyleSheet("background: transparent;")
        self.list_host = QWidget()
        self.list_host.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(14, 0, 14, 0)
        self.list_layout.setSpacing(0)
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)

        self.refresh()

    # ---------- data ----------
    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self._set_message("Loading the standings…")
        run_async(lambda: get_leaderboard(limit=10), self._show_entries, fail=self._show_error)

    def _show_entries(self, entries):
        self._loading = False
        self._clear_list()
        if not entries:
            self._set_message("No data yet — be the first!")
            return
        for rank, entry in enumerate(entries, start=1):
            self.list_layout.addWidget(self._make_row(rank, entry))
        self.list_layout.addStretch(1)

    def _show_error(self, _msg):
        self._loading = False
        self._set_message("Could not load the leaderboard.")

    # ---------- list helpers ----------
    def _clear_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _set_message(self, text):
        self._clear_list()
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"background: rgba(4,6,12,170); border-radius: 10px; padding: 10px 16px;"
            f" color: {T.dim}; font-family: '{FONT}'; font-size: 12pt;")
        self.list_layout.addSpacing(40)
        self.list_layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        self.list_layout.addStretch(1)

    def _make_row(self, rank, entry):
        is_me = entry["uid"] == self.current_uid
        top = TOP_STYLE.get(rank)
        accent = T.me if is_me else (top[2] if top else T.accent)

        row = GlowCard(accent=accent, radius=12)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(row.RING + 12, row.RING + 7, row.RING + 16, row.RING + 7)
        lay.setSpacing(12)

        lay.addWidget(RankBadge(rank))

        info = QVBoxLayout()
        info.setSpacing(0)
        name = QLabel(entry["name"] + ("  (you)" if is_me else ""))
        name.setStyleSheet(f"color: {T.me if is_me else T.text}; font-family: '{FONT}';"
                           f" font-size: 12pt; font-weight: bold;")
        sessions = QLabel(f"{entry['sessions']} sessions")
        sessions.setStyleSheet(f"color: {T.dim}; font-size: 9pt;")
        info.addWidget(name)
        info.addWidget(sessions)
        lay.addLayout(info, 1)

        minutes = QLabel(f"{entry['minutes']} min")
        minutes.setStyleSheet(f"color: {T.accent_hi}; font-family: '{FONT}';"
                              f" font-size: 13pt; font-weight: bold;")
        lay.addWidget(minutes)
        return row