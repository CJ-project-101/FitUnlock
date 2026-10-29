import os, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import math
import subprocess
import time
from PySide6.QtCore import (QObject, Signal, Slot, Property, QUrl, QTimer, QSettings,
                            QAbstractListModel, QModelIndex, Qt)
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from api import Api, BASE

PAGE = 20
MAX_BYTES = 100 * 1024 * 1024
ALLOWED = {".mp4", ".mov", ".webm", ".mkv"}      # matches the server
KEYS = ["reelId", "author", "caption", "videoUrl", "thumbUrl", "likes", "comments", "liked"]
ROLE = {k: int(Qt.ItemDataRole.UserRole) + 1 + i for i, k in enumerate(KEYS)}


FITPLAY_ROOT = Path(r"D:\Major project")                         # EDIT
FITPLAY_MAIN = FITPLAY_ROOT / "python_app" / "main.py"           # EDIT
FITPLAY_PY = FITPLAY_ROOT / "venv" / "Scripts" / "python.exe"    # FitPlay's own venv (MediaPipe lives there)



def convert(d):
    """Server reel dict -> flat dict used by the QML model."""
    return {"reelId": d["id"], "author": d["author"], "caption": d.get("caption") or "",
            "videoUrl": BASE + d["video_url"],
            "thumbUrl": (BASE + d["thumb_url"]) if d.get("thumb_url") else "",
            "likes": d["likes"], "comments": d["comments"], "liked": d["liked"]}


class ReelModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items, self._ids = [], set()

    def roleNames(self):
        return {ROLE[k]: k.encode() for k in KEYS}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        i = role - int(Qt.ItemDataRole.UserRole) - 1
        return self._items[index.row()][KEYS[i]] if 0 <= i < len(KEYS) else None

    def reset(self, items):
        self.beginResetModel()
        self._items = list(items)
        self._ids = {x["reelId"] for x in self._items}
        self.endResetModel()

    def append(self, items):
        new = [x for x in items if x["reelId"] not in self._ids]   # no duplicates
        if not new:
            return 0
        n = len(self._items)
        self.beginInsertRows(QModelIndex(), n, n + len(new) - 1)
        self._items.extend(new)
        self._ids.update(x["reelId"] for x in new)
        self.endInsertRows()
        return len(new)

    def find(self, reel_id):
        for i, x in enumerate(self._items):
            if x["reelId"] == reel_id:
                return i
        return -1

    def item(self, row):
        return dict(self._items[row]) if 0 <= row < len(self._items) else None

    def patch(self, row, **changes):
        if not (0 <= row < len(self._items)):
            return
        self._items[row].update(changes)
        idx = self.index(row)
        self.dataChanged.emit(idx, idx, [ROLE[k] for k in changes])


class Backend(QObject):
    _done = Signal(object)

    signedInChanged = Signal()
    busyChanged = Signal()
    authErrorChanged = Signal()
    usernameChanged = Signal()
    lockedChanged = Signal()
    gateTextChanged = Signal()
    loadingChanged = Signal()
    hasMoreChanged = Signal()
    uploadingChanged = Signal()

    toast = Signal(str)
    feedReloaded = Signal()
    viewerReady = Signal(int)
    commentsLoaded = Signal(int, list)
    commentsFailed = Signal(int, str)
    profileLoaded = Signal(str, dict)
    profileFailed = Signal(str, str)
    uploadSucceeded = Signal()
    uploadFailed = Signal(str)

    def __init__(self):
        super().__init__()
        self.api = Api()
        self._pool = ThreadPoolExecutor(max_workers=4)
        self._done.connect(self._dispatch)
        self._model = ReelModel(self)
        self._viewer = ReelModel(self)      # reels shown in the profile viewer
        self._settings = QSettings("Reelz", "Reelz")
        self._signed_in = self._busy = self._locked = False
        self._loading = self._uploading = False
        self._has_more = True
        self._auth_error = self._username = self._gate_text = ""
        self._likes_busy = set()
        # CHANGED: gate state (replaces the old _gate_busy + _gate_timer lines)
        self._gate_busy = False
        self._gate_again = False
        self._watching = False
        self._left = None            # seconds left as of _left_at (None = no countdown)
        self._left_at = 0.0
        self._gate_timer = QTimer(self)
        self._gate_timer.timeout.connect(self._poll_gate)
        self._tick_timer = QTimer(self)                  # smooth 1-second display countdown
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(1000)

    # ---------- plumbing ----------
    def _run(self, fn, ok=None, fail=None):
        def job():
            try:
                pack = (ok, fail, fn(), None)
            except Exception as e:
                pack = (ok, fail, None, e)
            self._done.emit(pack)          # delivered on the UI thread
        self._pool.submit(job)

    @Slot(object)
    def _dispatch(self, pack):
        ok, fail, res, exc = pack
        if exc is not None:
            if fail:
                fail(exc)
            else:
                self.toast.emit(str(exc))
        elif ok:
            ok(res)

    def _set(self, attr, value, signal):
        if getattr(self, attr) != value:
            setattr(self, attr, value)
            signal.emit()

    # ---------- properties ----------
    @Property(QObject, constant=True)
    def reels(self): return self._model

    @Property(QObject, constant=True)
    def viewer(self): return self._viewer

    @Property(bool, notify=signedInChanged)
    def signedIn(self): return self._signed_in

    @Property(bool, notify=busyChanged)
    def busy(self): return self._busy

    @Property(str, notify=authErrorChanged)
    def authError(self): return self._auth_error

    @Property(str, notify=usernameChanged)
    def username(self): return self._username

    @Property(bool, notify=lockedChanged)
    def locked(self): return self._locked

    @Property(str, notify=gateTextChanged)
    def gateText(self): return self._gate_text

    @Property(bool, notify=loadingChanged)
    def loading(self): return self._loading

    @Property(bool, notify=hasMoreChanged)
    def hasMore(self): return self._has_more

    @Property(bool, notify=uploadingChanged)
    def uploading(self): return self._uploading

    # ---------- auth ----------
    @Slot(str, str, str)
    def authenticate(self, username, password, mode):
        if self._busy:
            return
        self._set("_busy", True, self.busyChanged)
        self._set("_auth_error", "", self.authErrorChanged)

        def fail(e):
            self._set("_busy", False, self.busyChanged)
            self._set("_auth_error", str(e), self.authErrorChanged)
        self._run(lambda: self.api.auth(mode, username, password), lambda _: self._finish_login(), fail)

    @Slot()
    def restore(self):
        """Auto-login with the saved token, if it is still valid."""
        token = self._settings.value("token", "")
        name = self._settings.value("username", "")
        if not token or not name:
            return
        self.api.token, self.api.username = token, name

        def fail(_):
            self.api.token = self.api.username = None
            self._settings.remove("token")
        # CHANGED: validate with an endpoint that really needs a login (/gate does not)
        self._run(lambda: self.api.profile(name), lambda _: self._finish_login(), fail)

    def _finish_login(self):
        self._settings.setValue("token", self.api.token)
        self._settings.setValue("username", self.api.username)
        self._set("_busy", False, self.busyChanged)
        self._set("_username", self.api.username, self.usernameChanged)
        self._set("_signed_in", True, self.signedInChanged)
        self.loadFeed()
        self._gate_timer.start(5000)
        self._poll_gate()

    @Slot()
    def logout(self):
        # CHANGED: reset the gate state first
        self._watching = False
        self._left = None
        self._gate_timer.stop()
        self.api.token = self.api.username = None
        self._settings.remove("token"); self._settings.remove("username")
        self._model.reset([])
        self._set("_has_more", True, self.hasMoreChanged)
        self._set("_locked", False, self.lockedChanged)
        self._set("_signed_in", False, self.signedInChanged)

    # ---------- feed ----------
    @Slot()
    def loadFeed(self):
        self._fetch(reset=True)

    @Slot()
    def loadMore(self):
        if self._has_more:
            self._fetch(reset=False)

    def _fetch(self, reset):
        if self._loading:
            return
        offset = 0 if reset else self._model.rowCount()
        self._set("_loading", True, self.loadingChanged)

        def ok(items):
            conv = [convert(d) for d in items]
            if reset:
                self._model.reset(conv)
                self.feedReloaded.emit()
            else:
                self._model.append(conv)
            self._set("_has_more", len(items) >= PAGE, self.hasMoreChanged)
            self._set("_loading", False, self.loadingChanged)

        def fail(e):
            self._set("_loading", False, self.loadingChanged)
            if "Locked" not in str(e):          # CHANGED: no toast spam while locked
                self.toast.emit(str(e))
        self._run(lambda: self.api.feed(offset, PAGE), ok, fail)

    # ---------- likes ----------
    def _model_for(self, which):
        return self._viewer if which == "viewer" else self._model

    def _patch_all(self, rid, **changes):
        for m in (self._model, self._viewer):
            r = m.find(rid)
            if r >= 0:
                m.patch(r, **changes)

    @Slot(str, int)
    def toggleLikeIn(self, which, row):
        it = self._model_for(which).item(row)
        if not it or it["reelId"] in self._likes_busy:
            return
        rid, want = it["reelId"], not it["liked"]
        self._likes_busy.add(rid)
        self._patch_all(rid, liked=want, likes=it["likes"] + (1 if want else -1))   # optimistic

        def fail(e):
            self._likes_busy.discard(rid)
            self._patch_all(rid, liked=not want, likes=it["likes"])                 # put it back
            self.toast.emit(str(e))
        self._run(lambda: self.api.like(rid, want), lambda _: self._likes_busy.discard(rid), fail)

    @Slot(int)
    def toggleLike(self, row):
        self.toggleLikeIn("feed", row)

    # ---------- comments ----------
    @Slot(int)
    def loadComments(self, reel_id):
        def ok(rows):
            self._patch_all(reel_id, comments=len(rows))
            self.commentsLoaded.emit(reel_id, rows)
        self._run(lambda: self.api.comments(reel_id), ok,
                  lambda e: self.commentsFailed.emit(reel_id, str(e)))

    @Slot(int, str)
    def addComment(self, reel_id, text):
        self._run(lambda: self.api.add_comment(reel_id, text),
                  lambda _: self.loadComments(reel_id), lambda e: self.toast.emit(str(e)))

    # ---------- profiles ----------

    @Slot(str, int)
    def openUserReels(self, name, index):
        def ok(items):
            self._viewer.reset([convert(d) for d in items])
            self.viewerReady.emit(index)
        self._run(lambda: self.api.user_reels(name), ok, lambda e: self.toast.emit(str(e)))

    @Slot(str)
    def loadProfile(self, name):
        def ok(p):
            p["reels"] = [{"id": r["id"], "caption": r.get("caption") or "",
                           "thumbUrl": (BASE + r["thumb_url"]) if r.get("thumb_url") else ""}
                          for r in p["reels"]]
            self.profileLoaded.emit(name, p)
        self._run(lambda: self.api.profile(name), ok, lambda e: self.profileFailed.emit(name, str(e)))

    @Slot(str, bool)
    def setFollow(self, name, on):
        self._run(lambda: self.api.follow(name, on),
                  lambda _: self.loadProfile(name), lambda e: self.toast.emit(str(e)))

    # ---------- upload ----------
    @Slot(str, result="QVariantMap")
    def inspectFile(self, url):
        p = Path(QUrl(url).toLocalFile())
        if not p.is_file():
            return {"error": "File not found"}
        if p.suffix.lower() not in ALLOWED:
            return {"error": "Unsupported type. Use " + ", ".join(sorted(ALLOWED))}
        size = p.stat().st_size
        if size > MAX_BYTES:
            return {"error": "File is larger than 100 MB"}
        return {"name": p.name, "sizeMb": round(size / 1048576, 1), "error": ""}

    @Slot(str, str)
    def uploadReel(self, url, caption):
        if self._uploading:
            return
        path = QUrl(url).toLocalFile()
        self._set("_uploading", True, self.uploadingChanged)

        def ok(_):
            self._set("_uploading", False, self.uploadingChanged)
            self.uploadSucceeded.emit()
            self.toast.emit("Reel shared")
            self.loadFeed()

        def fail(e):
            self._set("_uploading", False, self.uploadingChanged)
            self.uploadFailed.emit(str(e))
        self._run(lambda: self.api.upload(path, caption), ok, fail)

    # ---------- FitPlay gate ----------
    # CHANGED: this whole section replaces the old _poll_gate
    @Slot(bool)
    def setWatching(self, on):
        """QML tells us when a reel starts or stops actually playing."""
        if on == self._watching:
            return
        self._fold()
        self._watching = on
        self._poll_gate()           # report immediately so the server's accounting is exact

    def _fold(self):
        """Bring the local countdown up to date before the watching flag changes."""
        if self._left is not None:
            now = time.monotonic()
            if self._watching:
                self._left = max(0.0, self._left - (now - self._left_at))
            self._left_at = now

    def _poll_gate(self):
        if not self._signed_in:
            return
        if self._gate_busy:
            self._gate_again = True       # run once more as soon as the current call ends
            return
        self._gate_busy = True
        watching = self._watching

        def done():
            self._gate_busy = False
            if self._gate_again:
                self._gate_again = False
                self._poll_gate()

        def ok(g):
            was_locked = self._locked
            unlocked = bool(g.get("unlocked"))
            s = g.get("seconds")
            self._left = float(s) if (unlocked and s is not None) else None
            self._left_at = time.monotonic()
            self._set("_locked", not unlocked, self.lockedChanged)
            self._show_left()
            if unlocked and was_locked and self._model.rowCount() == 0:
                self.loadFeed()           # the feed could not load while locked
            done()

        self._run(lambda: self.api.tick(watching), ok, lambda e: done())

    def _show_left(self):
        if self._left is None:
            self._set("_gate_text", "", self.gateTextChanged)
            return None
        left = self._left
        if self._watching and not self._locked:
            left -= time.monotonic() - self._left_at
        s = max(0, math.ceil(left))
        self._set("_gate_text", f"{s // 60}:{s % 60:02d} left", self.gateTextChanged)
        return s

    def _tick(self):
        s = self._show_left()
        if s == 0 and self._watching:
            self._poll_gate()             # the server decides; normally "locked" now

    @Slot()
    def openFitPlay(self):
        if not FITPLAY_MAIN.is_file() or not FITPLAY_PY.is_file():
            self.toast.emit("FitPlay not found - check the paths at the top of main.py")
            return
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            subprocess.Popen([str(FITPLAY_PY), str(FITPLAY_MAIN)],
                             cwd=str(FITPLAY_MAIN.parent), creationflags=flags)
            self.toast.emit("Opening FitPlay... if it is already open, switch to its window")
        except OSError as e:
            self.toast.emit(str(e))

    @Slot()
    def shutdown(self):
        """App is closing: give unused time back to the FitPlay bank."""
        self._watching = False
        try:
            self.api.gate_end()
        except Exception:
            pass


def main():
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    fmt = QSurfaceFormat()
    fmt.setSamples(4)                       # smooth vector icons
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Reelz")
    QQuickStyle.setStyle("Basic")

    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        sys.exit(1)
    QTimer.singleShot(0, backend.restore)
    app.aboutToQuit.connect(backend.shutdown)      # CHANGED: refund unused time on exit
    sys.exit(app.exec())


if __name__ == "__main__":
    main()