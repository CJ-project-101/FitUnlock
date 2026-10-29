"""
FitPlay visual toolkit: theme engine, animated backdrops, glow cards and buttons,
gradient text, logo and heat meter. Pure QPainter, no image files needed.

Switch themes with set_theme("cobalt"). Pages read the active theme (T) when they are
built, so after set_theme() rebuild the page to see the new look.
"""
import json
import math
import random
import time
from pathlib import Path

from PySide6.QtCore import (Qt, QTimer, QRectF, QPointF, QSize, QVariantAnimation,
                            QEasingCurve, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QLinearGradient,
                           QPainter, QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QWidget

FONT = "Segoe UI"
DEFAULT_THEME = "cobalt"
_SAVE_PATH = Path(__file__).with_name("theme.json")

# ─────────────────────────────────────────────────────────────
# THEMES
# ─────────────────────────────────────────────────────────────
THEMES = {
    # ── Cobalt Noir: black, cobalt / royal blue, pure white ──────────────
    "cobalt": dict(
        name="Cobalt Noir",
        mood="Black, cobalt and pure white. Clean, luxurious, tech-premium.",
        bg=("#03050a", "#060b18", "#0a1736"),
        glow_bottom=(40, 100, 255, 90),
        accent="#2f6bff", accent_hi="#8fb2ff", accent_lo="#0047ab",
        text="#f5f8ff", dim="#8fa0c0",
        success="#3ee6b0", error="#ff6b81", warn="#ffc15a",
        title=("#ffffff", "#c4d6ff", "#5b8cff"),
        card_top=(14, 22, 44, 235), card_bottom=(7, 11, 24, 235),
        btn_primary=dict(colors=("#6c9bff", "#2f6bff", "#0b3fb8"), glow="#2f6bff", text="#ffffff"),
        btn_secondary=dict(colors=("#ffffff", "#eef3ff", "#cfd9f0"), glow="#cfe0ff",
                           text="#08122e", hover="darker"),
        btn_ghost=dict(colors=("#1a2640", "#121b30", "#0b1222"), glow="#2f6bff", text="#f5f8ff"),
        activity=("#2f6bff", "#4dc3ff", "#9b8cff", "#3ee6b0"),
        me="#ffffff",
        orbs=(("#0047ab", 120, 0.55, 0.11, 0.0, 0.0),
              ("#4169e1", 80, 0.45, 0.08, 2.1, 1.3)),
        waves=dict(power=1.0, layers=(
            (6, 26, 0.012, 0.031, 0.6, 1.1, (47, 107, 255), (0, 71, 171), 70),
            (4, 18, 0.017, 0.043, 0.9, 1.5, (143, 178, 255), (65, 105, 225), 85))),
        particles=dict(count=40, colors=((190, 215, 255), (255, 255, 255), (120, 160, 255)),
                       speed=(6, 22), size=(0.8, 2.2), sway=(4, 14), fade=False),
        logo=dict(top="#cfe0ff", mid="#2f6bff", bottom="#0a3aa8",
                  core_top="#ffffff", core_bottom="#a9c8ff", glow=(47, 107, 255)),
    ),
    # ── Royal Ember: royal blue + tomato red + white ─────────────────────
    "royal": dict(
        name="Royal Ember",
        mood="Royal blue calm with a tomato-red action button. Sporty and energetic.",
        bg=("#04060f", "#080e2a", "#101c52"),
        glow_bottom=(65, 105, 225, 85),
        accent="#4169e1", accent_hi="#9db4ff", accent_lo="#1b3bbf",
        text="#f7f9ff", dim="#93a1c9",
        success="#38e0a2", error="#ff7b8a", warn="#ffc15a",
        title=("#ffffff", "#bcc9ff", "#6f8cff"),
        card_top=(16, 22, 52, 235), card_bottom=(8, 11, 30, 235),
        btn_primary=dict(colors=("#ff9a85", "#ff6347", "#d63a1c"), glow="#ff6347", text="#2a0802"),
        btn_secondary=dict(colors=("#ffffff", "#eef1fb", "#cfd6ee"), glow="#cdd8ff",
                           text="#0a1230", hover="darker"),
        btn_ghost=dict(colors=("#1b2550", "#121a3a", "#0a1128"), glow="#4169e1", text="#f7f9ff"),
        activity=("#6f8cff", "#ff6347", "#4dc3ff", "#ffc15a"),
        me="#ff9a85",
        orbs=(("#4169e1", 115, 0.55, 0.10, 0.0, 0.4),
              ("#ff6347", 45, 0.40, 0.07, 2.6, 1.0)),
        waves=dict(power=1.2, layers=(
            (6, 28, 0.013, 0.033, 0.7, 1.2, (65, 105, 225), (27, 59, 191), 75),
            (3, 16, 0.020, 0.047, 1.1, 1.7, (255, 99, 71), (214, 58, 28), 55))),
        particles=dict(count=40, colors=((170, 190, 255), (255, 255, 255), (255, 140, 120)),
                       speed=(8, 28), size=(0.8, 2.2), sway=(4, 16), fade=False),
        logo=dict(top="#ffc2b3", mid="#ff6347", bottom="#c0301a",
                  core_top="#fff1ec", core_bottom="#ffb4a0", glow=(255, 99, 71)),
    ),
    # ── Crimson Noir: charcoal black + crimson + white ───────────────────
    "crimson": dict(
        name="Crimson Noir",
        mood="Charcoal and crimson. Bold, dramatic, premium gaming.",
        bg=("#09090c", "#14121a", "#2b0c17"),
        glow_bottom=(220, 20, 60, 90),
        accent="#dc143c", accent_hi="#ff6b87", accent_lo="#8b0a26",
        text="#fbf7f8", dim="#b3a2a8",
        success="#5be3a8", error="#ffa05a", warn="#ffd166",
        title=("#ffffff", "#ffd0d9", "#ff4d6d"),
        card_top=(28, 20, 28, 235), card_bottom=(14, 10, 16, 235),
        btn_primary=dict(colors=("#ff5c7a", "#dc143c", "#9b0b29"), glow="#dc143c", text="#ffffff"),
        btn_secondary=dict(colors=("#ffffff", "#f3f1f2", "#d7d3d5"), glow="#ffd0d9",
                           text="#1a0a0e", hover="darker"),
        btn_ghost=dict(colors=("#2a2329", "#1c181d", "#111014"), glow="#dc143c", text="#fbf7f8"),
        activity=("#dc143c", "#ff7a59", "#ff8fa3", "#c9ced6"),
        me="#ffffff",
        orbs=(("#dc143c", 95, 0.55, 0.10, 0.5, 0.0),
              ("#9aa4b2", 30, 0.40, 0.07, 2.4, 1.5)),
        waves=dict(power=1.7, layers=(
            (8, 40, 0.017, 0.049, 1.0, 1.8, (255, 60, 100), (155, 10, 40), 80),
            (5, 26, 0.026, 0.067, 1.6, 2.4, (255, 107, 135), (220, 20, 60), 95))),
        particles=dict(count=42, colors=((255, 90, 120), (255, 150, 170), (220, 20, 60)),
                       speed=(18, 60), size=(1.0, 2.8), sway=(5, 20), fade=True),
        logo=dict(top="#ffb3c1", mid="#dc143c", bottom="#7a0820",
                  core_top="#ffffff", core_bottom="#ffc2cf", glow=(220, 20, 60)),
    ),
    # ── Emerald Noir: charcoal black + forest green + white ──────────────
    "emerald": dict(
        name="Emerald Noir",
        mood="Charcoal and forest green. Calm, healthy, wellness-premium.",
        bg=("#050908", "#0a1511", "#0c2a1e"),
        glow_bottom=(30, 160, 90, 85),
        accent="#1fa05a", accent_hi="#7ff0b5", accent_lo="#0b5d3b",
        text="#f3fbf6", dim="#8fb2a0",
        success="#7ff0b5", error="#ff6b6b", warn="#ffd166",
        title=("#ffffff", "#c9f7de", "#3ed487"),
        card_top=(14, 28, 22, 235), card_bottom=(7, 14, 11, 235),
        btn_primary=dict(colors=("#5be39a", "#1fa05a", "#0b6b3e"), glow="#1fa05a", text="#03140a"),
        btn_secondary=dict(colors=("#ffffff", "#eefaf3", "#cfe8da"), glow="#c9f7de",
                           text="#06190f", hover="darker"),
        btn_ghost=dict(colors=("#18271f", "#101c16", "#09110d"), glow="#1fa05a", text="#f3fbf6"),
        activity=("#1fa05a", "#b6f56e", "#2dd4bf", "#e8c766"),
        me="#ffffff",
        orbs=(("#0b5d3b", 125, 0.55, 0.09, 0.0, 0.0),
              ("#1fa05a", 70, 0.42, 0.07, 2.0, 1.2)),
        waves=dict(power=1.0, layers=(
            (6, 24, 0.011, 0.029, 0.5, 0.9, (31, 160, 90), (11, 93, 59), 70),
            (4, 16, 0.016, 0.040, 0.8, 1.3, (127, 240, 181), (31, 160, 90), 80))),
        particles=dict(count=38, colors=((170, 240, 200), (255, 255, 255), (90, 220, 150)),
                       speed=(6, 20), size=(0.8, 2.2), sway=(4, 14), fade=False),
        logo=dict(top="#c9f7de", mid="#1fa05a", bottom="#0a5c38",
                  core_top="#ffffff", core_bottom="#a8f0c8", glow=(31, 160, 90)),
    ),
    # ── Inferno: the original flames ─────────────────────────────────────
    "inferno": dict(
        name="Inferno",
        mood="Flames and embers. Hot and loud.",
        bg=("#07030a", "#14060a", "#3a0e06"),
        glow_bottom=(255, 110, 20, 120),
        accent="#ff7a18", accent_hi="#ffd84d", accent_lo="#ff3b1f",
        text="#fff4e6", dim="#d9a68c",
        success="#8dffb0", error="#ff6b81", warn="#ffb02e",
        title=("#ffd84d", "#ff7a18", "#ff3b1f"),
        card_top=(34, 12, 8, 232), card_bottom=(16, 6, 5, 232),
        btn_primary=dict(colors=("#ffd84d", "#ff7a18", "#ff3b1f"), glow="#ff7a18", text="#2a0902"),
        btn_secondary=dict(colors=("#ff8fb0", "#ff2e7e", "#b3124a"), glow="#ff2e7e", text="#2a0210"),
        btn_ghost=dict(colors=("#3b1a12", "#2a120d", "#1c0a07"), glow="#ff7a18", text="#fff4e6"),
        activity=("#ff4d2e", "#ffb02e", "#ff2e7e", "#ffd84d"),
        me="#3ee6ff",
        orbs=(),
        waves=dict(power=2.0, layers=(
            (14, 74, 0.021, 0.055, 1.3, 2.1, (255, 40, 15), (190, 20, 8), 95),
            (10, 56, 0.030, 0.071, 1.9, 2.9, (255, 100, 20), (230, 60, 10), 120),
            (6, 38, 0.041, 0.093, 2.6, 3.7, (255, 190, 60), (255, 120, 20), 140))),
        particles=dict(count=46, colors=((255, 110, 25), (255, 170, 60), (255, 215, 110)),
                       speed=(22, 80), size=(1.0, 3.2), sway=(6, 26), fade=True),
        logo=dict(top="#ffd84d", mid="#ff7a18", bottom="#e2200f",
                  core_top="#fff7d6", core_bottom="#ffc947", glow=(255, 140, 30)),
    ),
}


class _Active:
    """The active theme. Attributes mirror the keys of the chosen THEMES entry."""
    key = DEFAULT_THEME

    def apply(self, key):
        spec = THEMES[key]
        self.key = key
        for k, v in spec.items():
            setattr(self, k, v)


T = _Active()


def _load_saved():
    try:
        key = json.loads(_SAVE_PATH.read_text(encoding="utf-8")).get("theme")
        if key in THEMES:
            return key
    except (OSError, ValueError):
        pass
    return DEFAULT_THEME


def set_theme(key):
    """Activates a theme and remembers it. Rebuild your pages afterwards."""
    if key not in THEMES:
        return
    T.apply(key)
    try:
        _SAVE_PATH.write_text(json.dumps({"theme": key}), encoding="utf-8")
    except OSError as e:
        print(f"[fx] could not save theme: {e}")
    apply_global_style()


def global_qss():
    """Styles for message boxes, tooltips and scrollbars so they match the theme."""
    r, g, b, _ = QColor(T.accent).getRgb()
    btn_text = T.btn_primary["text"]
    return f"""
QToolTip {{ background: {T.bg[1]}; color: {T.text}; border: 1px solid rgba({r},{g},{b},140); padding: 4px 8px; }}
QMessageBox {{ background: {T.bg[1]}; }}
QMessageBox QLabel {{ color: {T.text}; font-family: "{FONT}"; font-size: 10pt; }}
QMessageBox QPushButton {{ background: {T.accent}; color: {btn_text}; border: none; border-radius: 8px;
                           padding: 6px 18px; min-width: 70px; font-weight: bold; }}
QMessageBox QPushButton:hover {{ background: {T.accent_hi}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: rgba({r},{g},{b},120); border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba({r},{g},{b},190); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""


def apply_global_style():
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(global_qss())


# ─────────────────────────────────────────────────────────────
# SMALL HELPERS
# ─────────────────────────────────────────────────────────────

def rgba(color, alpha):
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c


def _pen(color, width):
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    return pen


def make_divider():
    """A thin glowing horizontal line in the accent color."""
    r, g, b, _ = QColor(T.accent).getRgb()
    d = QFrame()
    d.setFixedHeight(2)
    d.setStyleSheet(
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
        f" stop:0 rgba({r},{g},{b},0), stop:0.5 rgba({r},{g},{b},230), stop:1 rgba({r},{g},{b},0));"
        f" border: none;")
    return d


# ─────────────────────────────────────────────────────────────
# ANIMATED BACKDROP
# ─────────────────────────────────────────────────────────────

class _Particle:
    __slots__ = ("x", "y", "vy", "sway", "phase", "size", "color")


class BackdropPage(QWidget):
    """Base page: themed gradient, drifting orbs, waves or flames along the bottom and
    floating particles. Put your content in layouts on top of it."""
    FRAME_MS = 40        # 40 ms is about 25 frames per second

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._rng = random.Random()
        self._parts = []
        self._t0 = time.monotonic()
        self._last = self._t0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.FRAME_MS)

    def _spawn(self, w, h, anywhere=False):
        cfg = T.particles
        r = self._rng
        p = _Particle()
        p.x = r.uniform(0, w)
        p.y = r.uniform(0, h) if anywhere else h + r.uniform(0, 30)
        p.vy = r.uniform(*cfg["speed"])
        p.sway = r.uniform(*cfg["sway"])
        p.phase = r.uniform(0, math.tau)
        p.size = r.uniform(*cfg["size"])
        p.color = r.choice(cfg["colors"])
        return p

    def _tick(self):
        if not self.isVisible():          # hidden (exercise / game running): do nothing
            self._last = time.monotonic()
            return
        now = time.monotonic()
        dt = min(now - self._last, 0.1)
        self._last = now
        w, h = self.width(), self.height()
        if w < 10 or h < 10:
            return
        count = T.particles["count"]
        if len(self._parts) != count:
            self._parts = [self._spawn(w, h, anywhere=True) for _ in range(count)]
        for i, e in enumerate(self._parts):
            e.y -= e.vy * dt
            e.phase += dt * 1.6
            if e.y < -10:
                self._parts[i] = self._spawn(w, h)
        self.update()

    def paintEvent(self, _event):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1) base gradient
        top, mid, bot = T.bg
        base = QLinearGradient(0, 0, 0, h)
        base.setColorAt(0.0, QColor(top))
        base.setColorAt(0.55, QColor(mid))
        base.setColorAt(1.0, QColor(bot))
        p.fillRect(self.rect(), QBrush(base))

        # 2) slowly drifting light orbs
        self._paint_orbs(p, w, h)

        # 3) glow rising from the bottom
        gr, gg, gb, ga = T.glow_bottom
        glow = QRadialGradient(QPointF(w / 2, h * 1.02), h * 0.8)
        glow.setColorAt(0.0, QColor(gr, gg, gb, ga))
        glow.setColorAt(0.5, QColor(gr, gg, gb, int(ga * 0.38)))
        glow.setColorAt(1.0, QColor(gr, gg, gb, 0))
        p.fillRect(self.rect(), QBrush(glow))

        # 4) waves / flames
        self._paint_waves(p, w, h)

        # 5) vignette
        vig = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.8)
        vig.setColorAt(0.6, QColor(0, 0, 0, 0))
        vig.setColorAt(1.0, QColor(0, 0, 0, 150))
        p.fillRect(self.rect(), QBrush(vig))

        # 6) particles
        self._paint_particles(p, h)

    def _paint_orbs(self, p, w, h):
        if not T.orbs:
            return
        t = time.monotonic() - self._t0
        for hexcol, alpha, rf, speed, px, py in T.orbs:
            cx = w * (0.5 + 0.34 * math.sin(t * speed + px))
            cy = h * (0.38 + 0.22 * math.cos(t * speed * 0.8 + py))
            rad = max(w, h) * rf
            c0 = QColor(hexcol)
            c0.setAlpha(alpha)
            c1 = QColor(hexcol)
            c1.setAlpha(0)
            g = QRadialGradient(QPointF(cx, cy), rad)
            g.setColorAt(0.0, c0)
            g.setColorAt(1.0, c1)
            p.fillRect(self.rect(), QBrush(g))

    def _paint_waves(self, p, w, h):
        cfg = T.waves
        if not cfg:
            return
        t = time.monotonic() - self._t0
        power = cfg["power"]
        p.setPen(Qt.PenStyle.NoPen)
        for base, amp, f1, f2, s1, s2, tip, body, alpha in cfg["layers"]:
            path = QPainterPath()
            path.moveTo(0, h)
            x = 0.0
            step = 10.0
            while x <= w + step:
                a = 0.5 + 0.5 * math.sin(x * f1 + t * s1)
                b = 0.6 + 0.4 * math.sin(x * f2 - t * s2 + 1.7)
                path.lineTo(x, h - (base + amp * (a ** power) * b))
                x += step
            path.lineTo(w + step, h)
            path.closeSubpath()

            grad = QLinearGradient(0, h - base - amp, 0, h)
            grad.setColorAt(0.0, QColor(tip[0], tip[1], tip[2], 0))
            grad.setColorAt(0.45, QColor(body[0], body[1], body[2], int(alpha * 0.6)))
            grad.setColorAt(1.0, QColor(tip[0], tip[1], tip[2], alpha))
            p.setBrush(QBrush(grad))
            p.drawPath(path)

    def _paint_particles(self, p, h):
        fade = T.particles["fade"]
        p.setPen(Qt.PenStyle.NoPen)
        for e in self._parts:
            x = e.x + math.sin(e.phase) * e.sway
            flick = 0.65 + 0.35 * math.sin(e.phase * 3.1)
            if fade:                                   # embers dim as they rise
                life = max(0.0, min(1.0, e.y / h))
                a = int(255 * (0.15 + 0.85 * life) * flick)
            else:                                      # dust just twinkles
                a = int(200 * flick)
            r, g, b = e.color
            rad = e.size * 3.2
            grad = QRadialGradient(QPointF(x, e.y), rad)
            grad.setColorAt(0.0, QColor(min(255, r + 60), min(255, g + 60), min(255, b + 60), min(255, a)))
            grad.setColorAt(0.35, QColor(r, g, b, int(a * 0.55)))
            grad.setColorAt(1.0, QColor(r, g, b, 0))
            p.setBrush(QBrush(grad))
            p.drawEllipse(QPointF(x, e.y), rad, rad)


# ─────────────────────────────────────────────────────────────
# GLOW CARD
# ─────────────────────────────────────────────────────────────

class GlowCard(QFrame):
    """Glass card with a gradient border and a soft glow.
    The glow is drawn in the outer RING pixels, so give your layout at least that margin."""
    RING = 6
    clicked = Signal()

    def __init__(self, accent=None, clickable=False, radius=14):
        super().__init__()
        self._accent = QColor(accent or T.accent)
        self._radius = radius
        self._clickable = clickable
        self._hover = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_hover_value)
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_hover_value(self, v):
        self._hover = float(v)
        self.update()

    def _hover_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(float(self._hover))
        self._anim.setEndValue(float(target))
        self._anim.start()

    def enterEvent(self, event):
        if self._clickable:
            self._hover_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._clickable:
            self._hover_to(0.0)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if (self._clickable and event.button() == Qt.MouseButton.LeftButton
                and self.rect().contains(event.position().toPoint())):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(self.rect()).adjusted(self.RING, self.RING, -self.RING, -self.RING)
        r = self._radius
        a = self._accent

        # soft glow ring
        base = 28 + 110 * self._hover
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(self.RING):
            alpha = base * (1.0 - i / self.RING) ** 1.6
            p.setPen(_pen(rgba(a, alpha), 1.3))
            grow = i + 1
            p.drawRoundedRect(body.adjusted(-grow, -grow, grow, grow), r + grow, r + grow)

        # glass body
        fill = QLinearGradient(body.topLeft(), body.bottomLeft())
        fill.setColorAt(0.0, QColor(*T.card_top))
        fill.setColorAt(1.0, QColor(*T.card_bottom))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(body, r, r)

        # gradient border
        border = QLinearGradient(body.topLeft(), body.bottomRight())
        border.setColorAt(0.0, rgba(a, 150 + 100 * self._hover))
        border.setColorAt(0.5, rgba(T.accent, 80 + 90 * self._hover))
        border.setColorAt(1.0, rgba(a, 150 + 100 * self._hover))
        p.setPen(QPen(QBrush(border), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body, r, r)


# ─────────────────────────────────────────────────────────────
# GLOW BUTTON
# ─────────────────────────────────────────────────────────────

_PALETTE_KEYS = {"primary": "btn_primary", "secondary": "btn_secondary", "ghost": "btn_ghost"}


class GlowButton(QPushButton):
    """palette is 'primary' (hero action), 'secondary' (pearl or accent) or 'ghost' (glass)."""

    def __init__(self, text, palette="primary", pulse=False, height=44, font_px=15):
        super().__init__(text)
        pal = getattr(T, _PALETTE_KEYS[palette])
        self._colors = pal["colors"]
        self._glow = QColor(pal["glow"])
        self._text_color = QColor(pal["text"])
        self._hover_mode = pal.get("hover", "lighter")
        self._hover = 0.0
        self._pulse = 0.0
        self._pulse_on = pulse
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(height)
        f = QFont(FONT)
        f.setPixelSize(font_px)
        f.setBold(True)
        self.setFont(f)

        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover_value)

        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setDuration(1800)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setKeyValueAt(0.5, 1.0)
        self._pulse_anim.setEndValue(0.0)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.valueChanged.connect(self._on_pulse_value)

    def sizeHint(self):
        s = super().sizeHint()
        return QSize(s.width() + 38, max(s.height(), self.minimumHeight()))

    def _on_hover_value(self, v):
        self._hover = float(v)
        self.update()

    def _on_pulse_value(self, v):
        self._pulse = float(v)
        self.update()

    def _hover_to(self, target):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(float(self._hover))
        self._hover_anim.setEndValue(float(target))
        self._hover_anim.start()

    def enterEvent(self, event):
        self._hover_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_to(0.0)
        super().leaveEvent(event)

    def showEvent(self, event):
        if self._pulse_on:
            self._pulse_anim.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self._pulse_anim.stop()
        super().hideEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)

        rect = QRectF(self.rect()).adjusted(5, 5, -5, -5)
        if self.isDown():
            rect.translate(0, 1)
        rad = min(14.0, rect.height() / 2)

        # glow
        glow = 0.25 + 0.6 * self._hover + 0.35 * self._pulse
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(5):
            alpha = glow * 80 * (1.0 - i / 5)
            p.setPen(_pen(rgba(self._glow, alpha), 1.4))
            p.drawRoundedRect(rect.adjusted(-i - 1, -i - 1, i + 1, i + 1), rad + i + 1, rad + i + 1)

        # body
        c0, c1, c2 = (QColor(c) for c in self._colors)
        if self._hover > 0:
            if self._hover_mode == "darker":
                shade = 100 + int(8 * self._hover)
                c0, c1, c2 = c0.darker(shade), c1.darker(shade), c2.darker(shade)
            else:
                lift = 100 + int(16 * self._hover)
                c0, c1, c2 = c0.lighter(lift), c1.lighter(lift), c2.lighter(lift)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, c0)
        grad.setColorAt(0.55, c1)
        grad.setColorAt(1.0, c2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect, rad, rad)

        # gloss on the upper half
        gloss = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.center().y()))
        gloss.setColorAt(0.0, QColor(255, 255, 255, 70))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(gloss))
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -rect.height() / 2), rad, rad)

        # thin edge highlight
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(_pen(rgba(self._glow, 120 + 110 * self._hover), 1.1))
        p.drawRoundedRect(rect, rad, rad)

        # label
        p.setPen(self._text_color)
        p.setFont(self.font())
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())


# ─────────────────────────────────────────────────────────────
# GRADIENT TEXT, ICON BADGE, LOGO, HEAT BAR, THEME DOTS
# ─────────────────────────────────────────────────────────────

class GradientText(QWidget):
    """Text filled with a vertical gradient (theme title colors) and a soft glow."""

    def __init__(self, text, pixel_size=32, colors=None, align="center", glow=True):
        super().__init__()
        self._text = text
        self._colors = colors or T.title
        self._align = align
        self._glow = glow
        self._font = QFont(FONT)
        self._font.setPixelSize(pixel_size)
        self._font.setBold(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._fit()

    def setText(self, text):
        if text != self._text:
            self._text = text
            self._fit()
            self.update()

    def _fit(self):
        fm = QFontMetrics(self._font)
        self.setFixedHeight(fm.height() + 12)
        self.setMinimumWidth(fm.horizontalAdvance(self._text) + 16)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        fm = QFontMetrics(self._font)
        tw = fm.horizontalAdvance(self._text)
        x = (self.width() - tw) / 2 if self._align == "center" else 8
        y = 6 + fm.ascent()

        path = QPainterPath()
        path.addText(QPointF(x, y), self._font, self._text)

        if self._glow:
            gr, gg, gb, _ = QColor(T.accent).getRgb()
            p.setBrush(Qt.BrushStyle.NoBrush)
            for width, alpha in ((10, 22), (6, 38), (3, 64)):
                pen = _pen(QColor(gr, gg, gb, alpha), width)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.drawPath(path)

        grad = QLinearGradient(0, y - fm.ascent(), 0, y + fm.descent())
        n = len(self._colors)
        for i, c in enumerate(self._colors):
            grad.setColorAt(i / (n - 1) if n > 1 else 0.0, QColor(c))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)


class IconBadge(QWidget):
    """Glowing round badge with an emoji inside."""

    def __init__(self, emoji, accent, size=44):
        super().__init__()
        self.setFixedSize(size, size)
        self._emoji = emoji
        self._accent = QColor(accent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        c = QPointF(w / 2, self.height() / 2)
        r = w / 2 - 1
        a = self._accent

        g = QRadialGradient(c, r)
        g.setColorAt(0.0, rgba(a, 170))
        g.setColorAt(0.7, rgba(a, 60))
        g.setColorAt(1.0, rgba(a, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(c, r, r)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(_pen(rgba(a, 200), 1.5))
        p.drawEllipse(c, r * 0.72, r * 0.72)

        f = QFont("Segoe UI Emoji")
        f.setPixelSize(int(w * 0.42))
        p.setFont(f)
        p.setPen(QColor(T.text))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._emoji)


def _flame_outer(r):
    x, y, w, h = r.x(), r.y(), r.width(), r.height()

    def P(u, v):
        return QPointF(x + u * w, y + v * h)

    path = QPainterPath()
    path.moveTo(P(0.50, 0.00))
    path.cubicTo(P(0.50, 0.22), P(0.88, 0.40), P(0.88, 0.68))
    path.cubicTo(P(0.88, 0.88), P(0.72, 1.00), P(0.50, 1.00))
    path.cubicTo(P(0.28, 1.00), P(0.12, 0.88), P(0.12, 0.68))
    path.cubicTo(P(0.12, 0.52), P(0.22, 0.42), P(0.30, 0.30))
    path.cubicTo(P(0.33, 0.42), P(0.38, 0.46), P(0.44, 0.46))
    path.cubicTo(P(0.40, 0.30), P(0.44, 0.12), P(0.50, 0.00))
    path.closeSubpath()
    return path


def _flame_inner(r):
    x, y, w, h = r.x(), r.y(), r.width(), r.height()

    def P(u, v):
        return QPointF(x + u * w, y + v * h)

    path = QPainterPath()
    path.moveTo(P(0.50, 0.42))
    path.cubicTo(P(0.52, 0.55), P(0.72, 0.62), P(0.72, 0.80))
    path.cubicTo(P(0.72, 0.92), P(0.62, 0.98), P(0.50, 0.98))
    path.cubicTo(P(0.38, 0.98), P(0.28, 0.92), P(0.28, 0.80))
    path.cubicTo(P(0.28, 0.66), P(0.46, 0.58), P(0.50, 0.42))
    path.closeSubpath()
    return path


class FlameLogo(QWidget):
    """Animated flame emblem, recolored by the theme (a cobalt flame in Cobalt Noir)."""

    def __init__(self, width=76, height=88):
        super().__init__()
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._t0 = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(45)

    def _tick(self):
        if self.isVisible():
            self.update()

    def paintEvent(self, _event):
        t = time.monotonic() - self._t0
        lg = T.logo
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # pulsing glow
        gr, gg, gb = lg["glow"]
        pulse = 0.65 + 0.35 * math.sin(t * 3.0)
        center = QPointF(w / 2, h * 0.58)
        radius = min(w / 2, h * 0.5) - 1
        g = QRadialGradient(center, radius)
        g.setColorAt(0.0, QColor(gr, gg, gb, int(150 * pulse)))
        g.setColorAt(0.5, QColor(gr, gg, gb, int(60 * pulse)))
        g.setColorAt(1.0, QColor(gr, gg, gb, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(center, radius, radius)

        # flame, with a little flicker and sway around its base
        fw, fh = w * 0.52, h * 0.70
        rect = QRectF((w - fw) / 2, h * 0.14, fw, fh)
        base_x, base_y = rect.center().x(), rect.bottom()
        p.save()
        p.translate(base_x, base_y)
        p.rotate(1.8 * math.sin(t * 4.2))
        p.scale(1.0 + 0.04 * math.sin(t * 6.5), 1.0 + 0.05 * math.sin(t * 5.1 + 1.0))
        p.translate(-base_x, -base_y)

        outer = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        outer.setColorAt(0.0, QColor(lg["top"]))
        outer.setColorAt(0.45, QColor(lg["mid"]))
        outer.setColorAt(1.0, QColor(lg["bottom"]))
        p.setBrush(QBrush(outer))
        p.drawPath(_flame_outer(rect))

        inner = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        inner.setColorAt(0.0, QColor(lg["core_top"]))
        inner.setColorAt(1.0, QColor(lg["core_bottom"]))
        p.setBrush(QBrush(inner))
        p.drawPath(_flame_inner(rect))
        p.restore()


class HeatBar(QWidget):
    """Glowing meter showing how full the playtime bank is."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(22)
        self._value = 0.0
        self._target = 0.0
        self._t0 = time.monotonic()
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(600)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_value)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def set_fraction(self, f):
        f = max(0.0, min(1.0, float(f)))
        if abs(f - self._target) < 1e-4:
            return
        self._target = f
        self._anim.stop()
        self._anim.setStartValue(float(self._value))
        self._anim.setEndValue(f)
        self._anim.start()

    def _on_value(self, v):
        self._value = float(v)
        self.update()

    def _tick(self):
        if self.isVisible() and self._value > 0.001:
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QRectF(self.rect()).adjusted(4, 5, -4, -5)
        rad = track.height() / 2

        p.setPen(_pen(rgba(T.accent, 90), 1.2))
        p.setBrush(QColor(5, 8, 14, 200))
        p.drawRoundedRect(track, rad, rad)

        if self._value <= 0.001:
            return
        fill = QRectF(track.left(), track.top(),
                      max(track.height(), track.width() * self._value), track.height())

        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(4):
            p.setPen(_pen(rgba(T.accent, 70 * (1.0 - i / 4)), 1.2))
            p.drawRoundedRect(fill.adjusted(-i - 1, -i - 1, i + 1, i + 1), rad + i + 1, rad + i + 1)

        path = QPainterPath()
        path.addRoundedRect(fill, rad, rad)
        grad = QLinearGradient(fill.topLeft(), fill.topRight())
        grad.setColorAt(0.0, QColor(T.accent_lo))
        grad.setColorAt(0.55, QColor(T.accent))
        grad.setColorAt(1.0, QColor(T.accent_hi))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        # moving shimmer
        t = time.monotonic() - self._t0
        phase = (t * 90) % (fill.width() + 80) - 40
        p.save()
        p.setClipPath(path)
        sh = QLinearGradient(fill.left() + phase - 30, 0, fill.left() + phase + 30, 0)
        sh.setColorAt(0.0, QColor(255, 255, 255, 0))
        sh.setColorAt(0.5, QColor(255, 255, 255, 90))
        sh.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(sh))
        p.drawRect(fill)
        p.restore()


class ThemeDots(QWidget):
    """Row of small color dots, one per theme. Emits selected(key) when one is clicked."""
    selected = Signal(str)

    def __init__(self, size=16, gap=9):
        super().__init__()
        self._keys = list(THEMES.keys())
        self._size = size
        self._gap = gap
        self._hover = -1
        n = len(self._keys)
        self.setFixedSize(n * size + (n - 1) * gap + 10, size + 10)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def _rect(self, i):
        return QRectF(5 + i * (self._size + self._gap), 5, self._size, self._size)

    def _index_at(self, pt):
        for i in range(len(self._keys)):
            if self._rect(i).adjusted(-4, -4, 4, 4).contains(pt):
                return i
        return -1

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, key in enumerate(self._keys):
            spec = THEMES[key]
            r = self._rect(i)
            grad = QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0.0, QColor(spec["accent_hi"]))
            grad.setColorAt(1.0, QColor(spec["accent_lo"]))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(r)
            p.setBrush(Qt.BrushStyle.NoBrush)
            if key == T.key:
                p.setPen(_pen(T.text, 1.8))
                p.drawEllipse(r.adjusted(-3, -3, 3, 3))
            elif i == self._hover:
                p.setPen(_pen(rgba(T.text, 130), 1.2))
                p.drawEllipse(r.adjusted(-3, -3, 3, 3))

    def mouseMoveEvent(self, event):
        i = self._index_at(event.position())
        if i != self._hover:
            self._hover = i
            self.setToolTip(THEMES[self._keys[i]]["name"] if i >= 0 else "")
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover = -1
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        i = self._index_at(event.position())
        if i >= 0 and event.button() == Qt.MouseButton.LeftButton:
            key = self._keys[i]
            if key != T.key:
                self.selected.emit(key)
        super().mouseReleaseEvent(event)


# load the remembered theme as soon as this module is imported
T.apply(_load_saved())