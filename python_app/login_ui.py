import os
import sys
import queue
import threading
import tkinter as tk

sys.path.append(os.path.dirname(__file__))
from auth import create_user, verify_login_rest, init_firebase

# ─────────────────────────────────────────────────────────────
# THEME  (edit these to restyle the whole screen)
# ─────────────────────────────────────────────────────────────
BG = "#0b0b16"            # window background
CARD = "#15152a"          # card background
FIELD = "#1d1d38"         # input background
BORDER = "#2a2a4a"        # idle border
TEAL = "#0fd8a8"          # accent
TEAL_HOVER = "#2cf0c0"
TEAL_PRESS = "#0bb68d"
TEAL_DISABLED = "#2a5f55"
ON_TEAL = "#04231c"       # text on accent
TEXT = "#f2f2f7"
DIM = "#8a8a9e"
ERROR = "#ff5e7a"
WARN = "#ffb84d"

FONT = "Segoe UI"
F_TITLE = (FONT, 26, "bold")
F_SUB = (FONT, 10)
F_TAB = (FONT, 10, "bold")
F_LABEL = (FONT, 9, "bold")
F_ENTRY = (FONT, 11)
F_BTN = (FONT, 12, "bold")
F_SMALL = (FONT, 9)

FORM_W = 370
WIN_W, WIN_H = 480, 640


# ─────────────────────────────────────────────────────────────
# SMALL WIDGET HELPERS
# ─────────────────────────────────────────────────────────────

def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draws a rounded rectangle on a canvas."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class RoundedButton(tk.Canvas):
    """Accent button with rounded corners, hover and press states."""

    def __init__(self, parent, text, command, width, height=46, radius=14):
        super().__init__(parent, width=width, height=height, bg=CARD,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self._enabled = True
        self._shape = round_rect(self, 1, 1, width - 1, height - 1, radius,
                                 fill=TEAL, outline=TEAL)
        self._label = self.create_text(width // 2, height // 2, text=text,
                                       fill=ON_TEAL, font=F_BTN)
        self.bind("<Enter>", lambda e: self._paint(TEAL_HOVER))
        self.bind("<Leave>", lambda e: self._paint(TEAL))
        self.bind("<ButtonPress-1>", lambda e: self._paint(TEAL_PRESS))
        self.bind("<ButtonRelease-1>", self._on_release)

    def _paint(self, color):
        if self._enabled:
            self.itemconfig(self._shape, fill=color, outline=color)

    def _on_release(self, event):
        if not self._enabled:
            return
        self._paint(TEAL_HOVER)
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.command()

    def set_text(self, text):
        self.itemconfig(self._label, text=text)

    def set_enabled(self, enabled):
        self._enabled = enabled
        color = TEAL if enabled else TEAL_DISABLED
        self.itemconfig(self._shape, fill=color, outline=color)
        self.config(cursor="hand2" if enabled else "arrow")


class Field(tk.Frame):
    """Labelled input with a border that lights up on focus.
    Password fields get a Show/Hide toggle."""

    def __init__(self, parent, label, secret=False):
        super().__init__(parent, bg=CARD)
        self.secret = secret

        tk.Label(self, text=label.upper(), font=F_LABEL, bg=CARD, fg=DIM,
                 anchor="w").pack(fill="x")

        self.border = tk.Frame(self, bg=BORDER, padx=1, pady=1)
        self.border.pack(fill="x", pady=(5, 0))
        inner = tk.Frame(self.border, bg=FIELD)
        inner.pack(fill="x")

        self.entry = tk.Entry(inner, font=F_ENTRY, bg=FIELD, fg=TEXT,
                              insertbackground=TEXT, relief="flat", bd=0,
                              highlightthickness=0, show="•" if secret else "")
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 4), ipady=9)

        if secret:
            self.toggle = tk.Label(inner, text="Show", font=F_SMALL, bg=FIELD,
                                   fg=DIM, cursor="hand2", padx=10)
            self.toggle.pack(side="right")
            self.toggle.bind("<Button-1>", self._toggle_visibility)

        inner.bind("<Button-1>", lambda e: self.entry.focus_set())
        self.entry.bind("<FocusIn>", lambda e: self.border.config(bg=TEAL))
        self.entry.bind("<FocusOut>", lambda e: self.border.config(bg=BORDER))

    def _toggle_visibility(self, _event=None):
        hidden = self.entry.cget("show") == "•"
        self.entry.config(show="" if hidden else "•")
        self.toggle.config(text="Hide" if hidden else "Show")

    def get(self):
        return self.entry.get()

    def set(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def focus(self):
        self.entry.focus_set()

    def bind_return(self, callback):
        self.entry.bind("<Return>", lambda e: callback())

    def mark_error(self):
        self.border.config(bg=ERROR)


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


# ─────────────────────────────────────────────────────────────
# LOGIN SCREEN
# ─────────────────────────────────────────────────────────────

class LoginScreen:
    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success
        self.mode = "login"
        self._busy = False
        self._alive = True
        self._queue = queue.Queue()      # worker threads -> Tk main thread

        root.title("FitPlay — Sign in")
        root.configure(bg=BG)
        root.resizable(False, False)
        self._center(WIN_W, min(WIN_H, root.winfo_screenheight() - 80))

        init_firebase()
        self._build_shell()
        self._render_form()
        self._poll()

    # ---------- window ----------
    def _center(self, w, h):
        x = (self.root.winfo_screenwidth() - w) // 2
        y = max((self.root.winfo_screenheight() - h) // 2 - 20, 0)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ---------- static layout ----------
    def _build_shell(self):
        for w in self.root.winfo_children():
            w.destroy()

        border = tk.Frame(self.root, bg=BORDER, padx=1, pady=1)
        border.place(relx=0.5, rely=0.5, anchor="center")
        card = tk.Frame(border, bg=CARD, padx=36, pady=24)
        card.pack()
        tk.Frame(card, width=FORM_W, height=0, bg=CARD).pack()   # fixes card width

        # logo: rounded square with a dumbbell
        logo = tk.Canvas(card, width=60, height=60, bg=CARD, highlightthickness=0)
        round_rect(logo, 2, 2, 58, 58, 16, fill=TEAL, outline=TEAL)
        round_rect(logo, 8, 25, 13, 35, 2, fill=ON_TEAL, outline=ON_TEAL)
        round_rect(logo, 13, 19, 20, 41, 3, fill=ON_TEAL, outline=ON_TEAL)
        logo.create_rectangle(20, 28, 40, 32, fill=ON_TEAL, outline=ON_TEAL)
        round_rect(logo, 40, 19, 47, 41, 3, fill=ON_TEAL, outline=ON_TEAL)
        round_rect(logo, 47, 25, 52, 35, 2, fill=ON_TEAL, outline=ON_TEAL)
        logo.pack()

        title = tk.Frame(card, bg=CARD)
        title.pack(pady=(12, 0))
        tk.Label(title, text="FIT", font=F_TITLE, bg=CARD, fg=TEXT).pack(side="left")
        tk.Label(title, text="PLAY", font=F_TITLE, bg=CARD, fg=TEAL).pack(side="left")
        tk.Label(card, text="Move to unlock. Play to earn.", font=F_SUB,
                 bg=CARD, fg=DIM).pack(pady=(2, 18))

        self._build_tabs(card)

        self.form = tk.Frame(card, bg=CARD)
        self.form.pack(fill="x", pady=(18, 0))

        self.button = RoundedButton(card, "Log In", self._submit, FORM_W)
        self.button.pack(pady=(20, 0))

        self.status = tk.Label(card, text="", font=F_SMALL, bg=CARD, fg=ERROR,
                               wraplength=FORM_W, height=2, justify="center")
        self.status.pack(pady=(8, 0))

    def _build_tabs(self, parent):
        wrap = tk.Frame(parent, bg=FIELD, padx=4, pady=4)
        wrap.pack(fill="x")
        self._tabs = {}
        for key, text in (("login", "Log In"), ("signup", "Sign Up")):
            lbl = tk.Label(wrap, text=text, font=F_TAB, cursor="hand2", pady=8, width=14)
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, k=key: self._switch(k))
            self._tabs[key] = lbl

    def _style_tabs(self):
        for key, lbl in self._tabs.items():
            if key == self.mode:
                lbl.config(bg=TEAL, fg=ON_TEAL)
            else:
                lbl.config(bg=FIELD, fg=DIM)

    # ---------- dynamic form ----------
    def _render_form(self):
        for w in self.form.winfo_children():
            w.destroy()
        self._set_status("")
        self._style_tabs()

        if self.mode == "login":
            self.f_email = Field(self.form, "Email")
            self.f_email.pack(fill="x", pady=(0, 12))
            self.f_pass = Field(self.form, "Password", secret=True)
            self.f_pass.pack(fill="x")

            self.f_email.bind_return(self.f_pass.focus)
            self.f_pass.bind_return(self._submit)
            self.button.set_text("Log In")
            self.f_email.focus()
        else:
            self.f_name = Field(self.form, "Display name")
            self.f_name.pack(fill="x", pady=(0, 12))
            self.f_email = Field(self.form, "Email")
            self.f_email.pack(fill="x", pady=(0, 12))
            self.f_pass = Field(self.form, "Password (min 6 characters)", secret=True)
            self.f_pass.pack(fill="x")
            self._build_strength(self.form)

            self.f_name.bind_return(self.f_email.focus)
            self.f_email.bind_return(self.f_pass.focus)
            self.f_pass.bind_return(self._submit)
            self.f_pass.entry.bind("<KeyRelease>", self._update_strength)
            self.button.set_text("Create Account")
            self.f_name.focus()

    def _build_strength(self, parent):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(10, 0))
        self._segments = []
        for _ in range(3):
            seg = tk.Frame(row, bg=FIELD, height=4)
            seg.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self._segments.append(seg)
        self._strength_lbl = tk.Label(row, text="", font=F_SMALL, bg=CARD,
                                      fg=DIM, width=9, anchor="e")
        self._strength_lbl.pack(side="right")

    def _update_strength(self, _event=None):
        pw = self.f_pass.get()
        score = _strength(pw)
        colors = {1: ERROR, 2: WARN, 3: TEAL}
        names = {0: "Too short" if pw else "", 1: "Weak", 2: "Okay", 3: "Strong"}
        for i, seg in enumerate(self._segments):
            seg.config(bg=colors[score] if i < score else FIELD)
        self._strength_lbl.config(text=names[score], fg=colors.get(score, DIM))

    # ---------- status / busy ----------
    def _set_status(self, text, kind="error"):
        color = {"error": ERROR, "info": DIM, "success": TEAL}[kind]
        self.status.config(text=text, fg=color)

    def _begin(self, button_text):
        self._busy = True
        self.button.set_enabled(False)
        self.button.set_text(button_text)
        self._set_status("")

    def _end(self):
        self._busy = False
        self.button.set_enabled(True)
        self.button.set_text("Log In" if self.mode == "login" else "Create Account")

    def _switch(self, mode):
        if self._busy or mode == self.mode:
            return
        self.mode = mode
        self._render_form()

    # ---------- background work (keeps the window responsive) ----------
    def _run(self, work, done):
        def target():
            try:
                result = work()
            except Exception as e:
                result = (False, str(e))
            self._queue.put(lambda: done(result))
        threading.Thread(target=target, daemon=True).start()

    def _poll(self):
        while True:
            try:
                fn = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception as e:
                print(f"[login_ui] callback error: {e}")
        if self._alive:
            try:
                self.root.after(50, self._poll)
            except tk.TclError:
                pass

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
            self._alive = False                  # stop polling; this screen is done
            self.root.resizable(True, True)      # main UI may need a resizable window
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