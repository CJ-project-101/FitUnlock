import sys, time
from PySide6.QtCore import Qt, QUrl, QTimer, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (QApplication, QWidget, QDialog, QMainWindow, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QStackedWidget, QFileDialog, QMessageBox)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from api import Api, BASE

APP_NAME = "Reelz"   # use your own name and logo

STYLE = """
QWidget { background:#000; color:#f5f5f5; font-size:14px; }
QLineEdit { background:#121212; border:1px solid #363636; border-radius:8px; padding:10px; }
QPushButton { background:#262626; border:none; border-radius:10px; padding:10px 16px; font-weight:600; }
QPushButton:hover { background:#3a3a3a; }
QListWidget { background:#000; border:none; }
"""

def err(parent, e):
    QMessageBox.warning(parent, APP_NAME, str(e))

# ---------------- login ----------------
class LoginDialog(QDialog):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.setWindowTitle(f"{APP_NAME} - Sign in")
        self.user, self.pw = QLineEdit(), QLineEdit()
        self.user.setPlaceholderText("Username")
        self.pw.setPlaceholderText("Password")
        self.pw.setEchoMode(QLineEdit.Password)
        login, signup = QPushButton("Log in"), QPushButton("Create account")
        login.clicked.connect(lambda: self.go("login"))
        signup.clicked.connect(lambda: self.go("signup"))
        self.pw.returnPressed.connect(lambda: self.go("login"))
        lay = QVBoxLayout(self)
        title = QLabel(APP_NAME); title.setStyleSheet("font-size:32px; font-weight:bold;")
        title.setAlignment(Qt.AlignCenter)
        for w in (title, self.user, self.pw, login, signup): lay.addWidget(w)
        self.setFixedWidth(320)

    def go(self, mode):
        try:
            self.api.auth(mode, self.user.text(), self.pw.text())
            self.accept()
        except Exception as e:
            err(self, e)

# ---------------- comments ----------------
class CommentsDialog(QDialog):
    def __init__(self, api, reel_id, parent=None):
        super().__init__(parent)
        self.api, self.rid = api, reel_id
        self.setWindowTitle("Comments"); self.resize(380, 500)
        self.list = QListWidget()
        self.box = QLineEdit(); self.box.setPlaceholderText("Add a comment...")
        send = QPushButton("Post")
        send.clicked.connect(self.post); self.box.returnPressed.connect(self.post)
        row = QHBoxLayout(); row.addWidget(self.box); row.addWidget(send)
        lay = QVBoxLayout(self); lay.addWidget(self.list); lay.addLayout(row)
        self.refresh()

    def refresh(self):
        self.list.clear()
        try:
            for c in self.api.comments(self.rid):
                self.list.addItem(f"@{c['author']}: {c['text']}")
        except Exception as e:
            err(self, e)

    def post(self):
        text = self.box.text().strip()
        if not text: return
        try:
            self.api.add_comment(self.rid, text)
            self.box.clear(); self.refresh()
        except Exception as e:
            err(self, e)

# ---------------- reels feed ----------------
class ClickableVideo(QVideoWidget):
    clicked = Signal()
    doubleClicked = Signal()
    # A double-click fires two release events, so play/pause toggles twice and cancels out.
    def mouseReleaseEvent(self, e): self.clicked.emit()
    def mouseDoubleClickEvent(self, e): self.doubleClicked.emit()

class ReelsPage(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api, self.reels, self.i = api, [], 0
        self.locked, self.loaded, self.cooldown = False, False, False
        self.setFocusPolicy(Qt.StrongFocus)

        self.video = ClickableVideo(); self.video.setFixedSize(405, 720)
        self.audio = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.video.clicked.connect(self.toggle_play)
        self.video.doubleClicked.connect(self.double_like)

        self.lock_label = QLabel("Locked\n\nEarn minutes in FitPlay to keep watching")
        self.lock_label.setAlignment(Qt.AlignCenter)
        self.lock_label.setFixedSize(405, 720)
        self.stack = QStackedWidget(); self.stack.setFixedSize(405, 720)
        self.stack.addWidget(self.video); self.stack.addWidget(self.lock_label)

        self.author = QLabel(); self.author.setStyleSheet("font-weight:bold;")
        self.caption = QLabel(); self.caption.setWordWrap(True); self.caption.setFixedWidth(405)
        left = QVBoxLayout(); left.addWidget(self.stack); left.addWidget(self.author); left.addWidget(self.caption)

        self.like_btn, self.cmt_btn = QPushButton(), QPushButton()
        up, down = QPushButton("▲"), QPushButton("▼")
        self.like_btn.clicked.connect(self.toggle_like)
        self.cmt_btn.clicked.connect(self.open_comments)
        up.clicked.connect(lambda: self.go(-1)); down.clicked.connect(lambda: self.go(1))
        right = QVBoxLayout()
        for w in (up, down): right.addWidget(w)
        right.addStretch(); right.addWidget(self.like_btn); right.addWidget(self.cmt_btn); right.addSpacing(120)

        root = QHBoxLayout(self); root.addStretch(); root.addLayout(left); root.addLayout(right); root.addStretch()

    # lifecycle: only the visible tab plays video
    def showEvent(self, e):
        super().showEvent(e)
        if not self.loaded: self.reload()
        elif not self.locked: self.player.play()
        self.setFocus()

    def hideEvent(self, e):
        super().hideEvent(e); self.player.pause()

    def reload(self):
        try:
            self.reels = self.api.feed(); self.loaded = True; self.i = 0
            self.show_reel()
        except Exception as e:
            err(self, e)

    def show_reel(self):
        if not self.reels:
            self.author.setText(""); self.caption.setText("No reels yet. Upload the first one!")
            self.like_btn.setText("♡ 0"); self.cmt_btn.setText("💬 0")
            return
        r = self.reels[self.i]
        self.player.setSource(QUrl(BASE + r["video_url"]))
        if not self.locked: self.player.play()
        self.author.setText(f"@{r['author']}")
        self.caption.setText(r["caption"])
        self.refresh_buttons()

    def refresh_buttons(self):
        r = self.reels[self.i]
        self.like_btn.setText(("♥ " if r["liked"] else "♡ ") + str(r["likes"]))
        self.cmt_btn.setText(f"💬 {r['comments']}")

    def go(self, step):
        if self.cooldown or not self.reels: return
        j = self.i + step
        if 0 <= j < len(self.reels):
            self.i = j; self.show_reel()
        self.cooldown = True
        QTimer.singleShot(350, lambda: setattr(self, "cooldown", False))

    def wheelEvent(self, e): self.go(-1 if e.angleDelta().y() > 0 else 1)
    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Down, Qt.Key_J): self.go(1)
        elif e.key() in (Qt.Key_Up, Qt.Key_K): self.go(-1)
        elif e.key() == Qt.Key_Space: self.toggle_play()
        elif e.key() == Qt.Key_L: self.toggle_like()

    def toggle_play(self):
        if self.locked: return
        if self.player.isPlaying(): self.player.pause()
        else: self.player.play()

    def toggle_like(self):
        if not self.reels: return
        r = self.reels[self.i]
        want = not r["liked"]
        r["liked"] = want; r["likes"] += 1 if want else -1; self.refresh_buttons()  # optimistic
        try:
            self.api.like(r["id"], want)
        except Exception as e:
            r["liked"] = not want; r["likes"] += -1 if want else 1; self.refresh_buttons(); err(self, e)

    def double_like(self):
        if self.reels and not self.reels[self.i]["liked"]: self.toggle_like()

    def open_comments(self):
        if not self.reels: return
        CommentsDialog(self.api, self.reels[self.i]["id"], self).exec()
        try:  # refresh the comment count
            self.reels[self.i]["comments"] = len(self.api.comments(self.reels[self.i]["id"]))
            self.refresh_buttons()
        except Exception: pass

    def set_locked(self, locked):
        if locked == self.locked: return
        self.locked = locked
        self.stack.setCurrentIndex(1 if locked else 0)
        if locked: self.player.pause()
        elif self.isVisible() and self.reels: self.player.play()

# ---------------- upload ----------------
class UploadPage(QWidget):
    uploaded = Signal()
    def __init__(self, api):
        super().__init__()
        self.api, self.path = api, None
        self.file_lbl = QLabel("No video selected")
        pick = QPushButton("Choose video..."); pick.clicked.connect(self.pick)
        self.caption = QLineEdit(); self.caption.setPlaceholderText("Write a caption...")
        self.btn = QPushButton("Share reel"); self.btn.clicked.connect(self.send)
        lay = QVBoxLayout(self); lay.addStretch()
        for w in (self.file_lbl, pick, self.caption, self.btn): lay.addWidget(w)
        lay.addStretch()
        self.setMaximumWidth(480)

    def pick(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choose a video", "", "Videos (*.mp4 *.mov *.webm *.mkv)")
        if p: self.path = p; self.file_lbl.setText(p)

    def send(self):
        if not self.path: return err(self, "Pick a video first")
        self.btn.setEnabled(False); self.btn.setText("Uploading...")
        QApplication.processEvents()
        try:
            self.api.upload(self.path, self.caption.text())
            self.path = None; self.file_lbl.setText("No video selected"); self.caption.clear()
            self.uploaded.emit()
        except Exception as e:
            err(self, e)
        finally:
            self.btn.setEnabled(True); self.btn.setText("Share reel")

# ---------------- profile ----------------
class ProfilePage(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api, self.name = api, None
        self.search = QLineEdit(); self.search.setPlaceholderText("Find a user by username")
        self.search.returnPressed.connect(lambda: self.load(self.search.text().strip()))
        self.head = QLabel(); self.head.setStyleSheet("font-size:20px; font-weight:bold;")
        self.stats = QLabel()
        self.follow_btn = QPushButton(); self.follow_btn.clicked.connect(self.toggle_follow)
        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.IconMode)
        self.grid.setIconSize(QSize(120, 213))
        self.grid.setResizeMode(QListWidget.Adjust)
        self.grid.setMovement(QListWidget.Static)
        self.grid.setSpacing(4)
        lay = QVBoxLayout(self)
        for w in (self.search, self.head, self.stats, self.follow_btn, self.grid): lay.addWidget(w)
        self.setMaximumWidth(480)

    def showEvent(self, e):
        super().showEvent(e); self.load(self.api.username)

    def load(self, name):
        if not name: return
        try:
            p = self.api.profile(name)
        except Exception as e:
            return err(self, e)
        self.name = p["username"]; self.i_follow = p["i_follow"]
        self.head.setText(f"@{p['username']}")
        self.stats.setText(f"{len(p['reels'])} reels   {p['followers']} followers   {p['following']} following")
        self.follow_btn.setVisible(not p["is_me"])
        self.follow_btn.setText("Unfollow" if p["i_follow"] else "Follow")
        self.grid.clear()
        for r in p["reels"]:
            item = QListWidgetItem()
            if r.get("thumb_url"):
                data = self.api.get_bytes(r["thumb_url"])
                pm = QPixmap()
                if data and pm.loadFromData(data):
                    item.setIcon(QIcon(pm))
            if item.icon().isNull():
                item.setText(r["caption"] or "(reel)")   # fallback if no thumbnail
            self.grid.addItem(item)
        for r in p["reels"]: self.grid.addItem(f"🎬 {r['caption'] or '(no caption)'}")

    def toggle_follow(self):
        try:
            self.api.follow(self.name, not self.i_follow); self.load(self.name)
        except Exception as e:
            err(self, e)

# ---------------- main window ----------------
class MainWindow(QMainWindow):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.setWindowTitle(APP_NAME); self.resize(900, 840)
        self.reels, self.upload, self.profile = ReelsPage(api), UploadPage(api), ProfilePage(api)
        self.pages = QStackedWidget()
        for p in (self.reels, self.upload, self.profile): self.pages.addWidget(p)
        self.upload.uploaded.connect(self.after_upload)

        nav = QVBoxLayout()
        logo = QLabel(APP_NAME); logo.setStyleSheet("font-size:24px; font-weight:bold;")
        nav.addWidget(logo)
        for i, label in enumerate(("Reels", "Upload", "Profile")):
            b = QPushButton(label); b.clicked.connect(lambda _, i=i: self.pages.setCurrentIndex(i)); nav.addWidget(b)
        nav.addStretch()
        self.gate_lbl = QLabel(""); nav.addWidget(self.gate_lbl)

        body = QWidget(); row = QHBoxLayout(body)
        row.addLayout(nav); row.addWidget(self.pages, 1)
        self.setCentralWidget(body)

        self.timer = QTimer(self); self.timer.timeout.connect(self.poll_gate); self.timer.start(5000)
        self.poll_gate()

    def after_upload(self):
        self.reels.loaded = False
        self.pages.setCurrentIndex(0)

    def poll_gate(self):
        try:
            g = self.api.gate()
        except Exception:
            return                      # server hiccup: keep the current state
        self.reels.set_locked(not g["unlocked"])
        s = g.get("seconds")
        self.gate_lbl.setText("" if s is None else f"Time left: {s // 60}:{s % 60:02d}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    from PySide6.QtGui import QFont
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    api = Api()
    if LoginDialog(api).exec() != QDialog.Accepted:
        sys.exit(0)
    win = MainWindow(api); win.show()
    sys.exit(app.exec())