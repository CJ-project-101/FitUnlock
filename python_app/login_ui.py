import os
import sys

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

sys.path.append(os.path.dirname(__file__))
from auth import create_user, verify_login_rest, init_firebase
from qtutil import run_async
from fx import (BackdropPage, GlowCard, GlowButton, GradientText, FlameLogo, ThemeDots,
                make_divider, set_theme, T, FONT)

FORM_W = 370


def _style():
    """Built when the screen is created, so it always uses the active theme."""
    r, g, b, _ = QColor(T.accent).getRgb()
    ink = T.btn_primary["text"]
    return f"""
QLabel#fieldLabel {{ color: {T.dim}; font-family: "{FONT}"; font-size: 9pt; font-weight: bold; background: transparent; }}
QLabel#strengthLabel {{ color: {T.dim}; font-size: 9pt; background: transparent; }}
QFrame#tabs {{ background: rgba(255,255,255,14); border-radius: 10px; }}
QPushButton#tab {{ background: transparent; color: {T.dim}; border: none; border-radius: 8px;
                   padding: 8px; font-family: "{FONT}"; font-size: 10pt; font-weight: bold; }}
QPushButton#tab:checked {{ color: {ink};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {T.accent_hi}, stop:1 {T.accent}); }}
QFrame#fieldBox {{ background: rgba(4,6,12,200); border: 1px solid rgba({r},{g},{b},90); border-radius: 10px; }}
QFrame#fieldBox[state="focus"] {{ background: rgba(14,20,34,225); border: 1px solid {T.accent_hi}; }}
QFrame#fieldBox[state="error"] {{ border: 1px solid {T.error}; }}
QLineEdit#fieldEntry {{ background: transparent; border: none; color: {T.text};
                        font-family: "{FONT}"; font-size: 11pt; padding: 9px 0px;
                        selection-background-color: {T.accent}; selection-color: {ink}; }}
QPushButton#showToggle {{ background: transparent; border: none; color: {T.dim};
                          font-family: "{FONT}"; font-size: 9pt; padding: 0px 10px; }}
QPushButton#showToggle:hover {{ color: {T.accent_hi}; }}
"""


class FocusLineEdit(QLineEdit):
    focusChanged = Signal(bool)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focusChanged.emit(True)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focusChanged.emit(False)


class Field(QWidget):
    """Labelled input whose border lights up on focus. Password fields get Show/Hide."""

    def __init__(self, label, secret=False):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        cap = QLabel(label.upper())
        cap.setObjectName("fieldLabel")
        lay.addWidget(cap)

        self.box = QFrame()
        self.box.setObjectName("fieldBox")
        self.box.setProperty("state", "idle")
        self.box.setMinimumHeight(42)
        row = QHBoxLayout(self.box)
        row.setContentsMargins(12, 0, 4, 0)
        row.setSpacing(0)

        self.entry = FocusLineEdit()
        self.entry.setObjectName("fieldEntry")
        if secret:
            self.entry.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.entry, 1)

        self.toggle = None
        if secret:
            self.toggle = QPushButton("Show")
            self.toggle.setObjectName("showToggle")
            self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.toggle.clicked.connect(self._toggle_visibility)
            row.addWidget(self.toggle)

        lay.addWidget(self.box)
        self.entry.focusChanged.connect(lambda has: self._set_state("focus" if has else "idle"))

    def _set_state(self, state):
        self.box.setProperty("state", state)
        self.box.style().unpolish(self.box)
        self.box.style().polish(self.box)

    def _toggle_visibility(self):
        hidden = self.entry.echoMode() == QLineEdit.EchoMode.Password
        self.entry.setEchoMode(QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)
        self.toggle.setText("Hide" if hidden else "Show")

    def get(self):
        return self.entry.text()

    def set(self, text):
        self.entry.setText(text)

    def focus(self):
        self.entry.setFocus()

    def bind_return(self, callback):
        self.entry.returnPressed.connect(callback)

    def mark_error(self):
        self._set_state("error")


def _strength(pw):
    """0 = too short, 1 = weak, 2 = okay, 3 = strong."""
    if len(pw) < 6:
        return 0
    has_alpha = any(c.isalpha() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    has_symbol = any(not c.isalnum() for c in pw)
    score = 1
    if len(pw) >= 8 and has_alpha and has_digit:
        score = 2
    if len(pw) >= 10 and has_alpha and has_digit and has_symbol:
        score = 3
    return score


class LoginScreen(BackdropPage):
    def __init__(self, shell, on_login_success, on_restyle=None):
        super().__init__()
        self.shell = shell
        self.on_login_success = on_login_success
        self.on_restyle = on_restyle       # called after a theme change to rebuild this screen
        self.mode = "login"
        self._busy = False

        shell.setWindowTitle("FitPlay — Sign in")
        self.setStyleSheet(_style())

        init_firebase()          # raises a clear error if auth.py is not configured
        self._build_shell()
        self._render_form()

    # ---------- static layout ----------
    def _build_shell(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        card = GlowCard(accent=T.accent, radius=20)
        card.setFixedWidth(FORM_W + 72 + 2 * card.RING)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(36 + card.RING, 14 + card.RING, 36 + card.RING, 14 + card.RING)
        lay.setSpacing(0)

        # logo + title
        head = QHBoxLayout()
        head.setSpacing(4)
        head.addStretch(1)
        head.addWidget(FlameLogo(64, 76))
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.addStretch(1)
        title_col.addWidget(GradientText("FITPLAY", 38, align="left"))
        tag = QLabel("Move to unlock. Play to earn.")
        tag.setStyleSheet(f"color: {T.accent_hi}; font-size: 10pt; font-weight: bold; padding-left: 8px;")
        title_col.addWidget(tag)
        title_col.addStretch(1)
        head.addLayout(title_col)
        head.addStretch(1)
        lay.addLayout(head)
        lay.addWidget(make_divider())
        lay.addSpacing(14)

        self._build_tabs(lay)
        lay.addSpacing(16)

        self.form = QWidget()
        self.form_layout = QVBoxLayout(self.form)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(0)
        lay.addWidget(self.form)
        lay.addSpacing(16)

        self.button = GlowButton("Log In", palette="primary", pulse=True, height=50, font_px=17)
        self.button.clicked.connect(self._submit)
        lay.addWidget(self.button)
        lay.addSpacing(4)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setMinimumHeight(30)
        lay.addWidget(self.status)

        # theme picker
        lay.addSpacing(4)
        vibe = QLabel("CHOOSE YOUR VIBE")
        vibe.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vibe.setStyleSheet(f"color: {T.dim}; font-size: 8pt; font-weight: bold;")
        lay.addWidget(vibe)
        dots = ThemeDots()
        dots.selected.connect(self._on_theme_selected)
        lay.addWidget(dots, 0, Qt.AlignmentFlag.AlignHCenter)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

    def _on_theme_selected(self, key):
        set_theme(key)
        if self.on_restyle:
            QTimer.singleShot(0, self.on_restyle)

    def _build_tabs(self, parent_layout):
        wrap = QFrame()
        wrap.setObjectName("tabs")
        row = QHBoxLayout(wrap)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(0)
        self._tab_buttons = {}
        for key, text in (("login", "Log In"), ("signup", "Sign Up")):
            b = QPushButton(text)
            b.setObjectName("tab")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked=False, k=key: self._switch(k))
            row.addWidget(b, 1)
            self._tab_buttons[key] = b
        parent_layout.addWidget(wrap)

    def _style_tabs(self):
        for key, b in self._tab_buttons.items():
            b.setChecked(key == self.mode)

    # ---------- dynamic form ----------
    def _clear_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render_form(self):
        self._clear_form()
        self._set_status("")
        self._style_tabs()

        if self.mode == "login":
            self.f_email = Field("Email")
            self.f_pass = Field("Password", secret=True)
            self.form_layout.addWidget(self.f_email)
            self.form_layout.addSpacing(12)
            self.form_layout.addWidget(self.f_pass)

            self.f_email.bind_return(self.f_pass.focus)
            self.f_pass.bind_return(self._submit)
            self.button.setText("Log In")
            self.f_email.focus()
        else:
            self.f_name = Field("Display name")
            self.f_email = Field("Email")
            self.f_pass = Field("Password (min 6 characters)", secret=True)
            self.form_layout.addWidget(self.f_name)
            self.form_layout.addSpacing(12)
            self.form_layout.addWidget(self.f_email)
            self.form_layout.addSpacing(12)
            self.form_layout.addWidget(self.f_pass)
            self._build_strength()

            self.f_name.bind_return(self.f_email.focus)
            self.f_email.bind_return(self.f_pass.focus)
            self.f_pass.bind_return(self._submit)
            self.f_pass.entry.textChanged.connect(self._update_strength)
            self.button.setText("Create Account")
            self.f_name.focus()

    def _build_strength(self):
        self.form_layout.addSpacing(10)
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self._segments = []
        for _ in range(3):
            seg = QFrame()
            seg.setFixedHeight(4)
            seg.setStyleSheet("background: rgba(255,255,255,25); border-radius: 2px;")
            row.addWidget(seg, 1)
            self._segments.append(seg)
        self._strength_lbl = QLabel("")
        self._strength_lbl.setObjectName("strengthLabel")
        self._strength_lbl.setFixedWidth(70)
        self._strength_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._strength_lbl)
        self.form_layout.addWidget(host)

    def _update_strength(self, _text=""):
        pw = self.f_pass.get()
        score = _strength(pw)
        colors = {1: T.error, 2: T.warn, 3: T.success}      # semantic colors, not brand colors
        names = {0: "Too short" if pw else "", 1: "Weak", 2: "Okay", 3: "Strong"}
        for i, seg in enumerate(self._segments):
            color = colors[score] if i < score else "rgba(255,255,255,25)"
            seg.setStyleSheet(f"background: {color}; border-radius: 2px;")
        self._strength_lbl.setStyleSheet(
            f"color: {colors.get(score, T.dim)}; font-size: 9pt; background: transparent;")
        self._strength_lbl.setText(names[score])

    # ---------- status / busy ----------
    def _set_status(self, text, kind="error"):
        color = {"error": T.error, "info": T.dim, "success": T.success}[kind]
        if text:
            self.status.setStyleSheet(
                f"background: rgba(4,6,12,170); border-radius: 8px; padding: 6px 10px;"
                f" color: {color}; font-size: 9pt;")
        else:
            self.status.setStyleSheet("background: transparent;")
        self.status.setText(text)

    def _begin(self, button_text):
        self._busy = True
        self.button.setEnabled(False)
        self.button.setText(button_text)
        self._set_status("")

    def _end(self):
        self._busy = False
        self.button.setEnabled(True)
        self.button.setText("Log In" if self.mode == "login" else "Create Account")

    def _switch(self, mode):
        if self._busy or mode == self.mode:
            self._style_tabs()          # a click on the active tab must not un-highlight it
            return
        self.mode = mode
        self._render_form()

    # ---------- background work ----------
    def _run(self, work, done):
        run_async(work, done, fail=lambda msg: done((False, msg)))

    # ---------- actions ----------
    def _submit(self):
        if self._busy:
            return
        if self.mode == "login":
            self._do_login()
        else:
            self._do_signup()

    def _do_login(self):
        email = self.f_email.get().strip()
        password = self.f_pass.get()

        if not email or not password:
            if not email:
                self.f_email.mark_error()
            if not password:
                self.f_pass.mark_error()
            self._set_status("Enter your email and password.")
            return

        self._begin("Signing in…")
        self._run(lambda: verify_login_rest(email, password),
                  lambda res: self._login_done(res, email))

    def _login_done(self, res, email):
        ok, result = res
        if ok:
            self.on_login_success(result, email)
        else:
            self._end()
            self._set_status(result)

    def _do_signup(self):
        name = self.f_name.get().strip()
        email = self.f_email.get().strip()
        password = self.f_pass.get()

        problems = False
        if not name:
            self.f_name.mark_error()
            problems = True
        if "@" not in email or "." not in email.split("@")[-1]:
            self.f_email.mark_error()
            problems = True
        if len(password) < 6:
            self.f_pass.mark_error()
            problems = True
        if problems:
            self._set_status("Check the highlighted fields. Password needs 6+ characters.")
            return

        self._begin("Creating account…")
        self._run(lambda: create_user(email, password, name),
                  lambda res: self._signup_done(res, email))

    def _signup_done(self, res, email):
        ok, result = res
        self._end()
        if ok:
            self.mode = "login"
            self._render_form()
            self.f_email.set(email)
            self.f_pass.focus()
            self._set_status("Account created! Log in to continue.", "success")
        else:
            self._set_status(result)