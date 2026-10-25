import json
import math
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

SHARED = Path(os.getenv("FITPLAY_SHARED", r"D:\Major project\shared"))   # EDIT
BANK_FILE = SHARED / "session.json"
SOCIAL_FILE = SHARED / "social_session.json"

DEV_OPEN = os.getenv("GATE_ENABLED", "1") == "0"   # GATE_ENABLED=0 -> always unlocked (UI work)
CLAIM_WINDOW = 600     # s allowed between "Watch Reels" and the first poll (launch + login)
STALE_AFTER = 45       # s without a heartbeat = Reelz is gone, refund the rest
MAX_STEP = 12          # never burn more than this per heartbeat

router = APIRouter()
_lock = threading.Lock()


# ---------- small file helpers ----------
def _read(path):
    for _ in range(5):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, OSError):
            time.sleep(0.05)
    return {}


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".gate.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    for _ in range(10):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.05)
    os.replace(tmp, path)


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _started_epoch(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").timestamp()
    except (TypeError, ValueError):
        return None


def _locked_record():
    return {"status": "locked", "seconds_remaining": 0, "started_at": "", "user": ""}


def _refund(seconds):
    """Put seconds back into FitPlay's bank (never touches other keys)."""
    if seconds <= 0:
        return
    raw = _read(BANK_FILE)
    cap = _to_int(raw.get("max_bank_seconds")) or 3600
    raw["banked_seconds"] = min(_to_int(raw.get("banked_seconds")) + seconds, cap)
    raw.setdefault("max_bank_seconds", cap)
    raw.setdefault("active_session", {"status": "locked", "seconds_remaining": 0, "started_at": ""})
    _write(BANK_FILE, raw)


# ---------- the core: one function decides everything ----------
def _evaluate(heartbeat=None):
    """Seconds left (float) while a Reels session is active, otherwise None.

    heartbeat=None  -> read only: nothing is saved
    heartbeat=bool  -> a client heartbeat: burn the time since the last one
                       (only if it was watching), then record the new state
    """
    with _lock:
        data = _read(SOCIAL_FILE) or _locked_record()
        now = time.time()

        if data.get("status") == "unlocked":            # FitPlay granted time: claim it
            secs = _to_int(data.get("seconds_remaining"))
            started = _started_epoch(data.get("started_at"))
            fresh = started is not None and -5 <= now - started <= CLAIM_WINDOW
            if secs > 0 and fresh:
                data = {"status": "running", "seconds_remaining": float(secs),
                        "started_at": data.get("started_at", ""), "user": data.get("user", ""),
                        "last_tick": now, "watching": False}
                _write(SOCIAL_FILE, data)
            else:
                _refund(secs)                            # never claimed in time
                _write(SOCIAL_FILE, _locked_record())
                return None

        if data.get("status") != "running":
            return None

        left = _to_float(data.get("seconds_remaining"))
        gap = max(0.0, now - _to_float(data.get("last_tick")))

        if gap > STALE_AFTER:                            # Reelz crashed or was killed
            _refund(math.floor(left))
            _write(SOCIAL_FILE, _locked_record())
            return None

        if data.get("watching"):
            left -= min(gap, MAX_STEP)

        if left <= 0:                                    # used up: nothing to refund
            _write(SOCIAL_FILE, _locked_record())
            return None

        if heartbeat is not None:
            data["seconds_remaining"] = left
            data["last_tick"] = now
            data["watching"] = bool(heartbeat)
            _write(SOCIAL_FILE, data)
        return left


def require_unlocked():
    """FastAPI dependency: refuse to serve content while locked."""
    if DEV_OPEN:
        return
    if _evaluate() is None:
        raise HTTPException(status_code=403, detail="Locked - earn minutes in FitPlay first")


def _payload(left):
    return {"unlocked": left is not None, "seconds": None if left is None else math.ceil(left)}


class Beat(BaseModel):
    watching: bool = False


@router.get("/gate")
def gate():
    """Read-only state. Handy in a browser for testing."""
    if DEV_OPEN:
        return {"unlocked": True, "seconds": None}
    return _payload(_evaluate())


@router.post("/gate/tick")
def gate_tick(b: Beat):
    """Heartbeat from the Reelz app."""
    if DEV_OPEN:
        return {"unlocked": True, "seconds": None}
    return _payload(_evaluate(heartbeat=b.watching))


@router.post("/gate/end")
def gate_end():
    """Reelz closed: give unused time back to the FitPlay bank."""
    if DEV_OPEN:
        return {"refunded": 0}
    left = _evaluate()                                   # also claims or cleans up
    if left is None:
        return {"refunded": 0}
    with _lock:
        data = _read(SOCIAL_FILE)
        if data.get("status") != "running":
            return {"refunded": 0}
        refunded = max(0, math.floor(left))
        _refund(refunded)
        _write(SOCIAL_FILE, _locked_record())
        return {"refunded": refunded}


# ---------- background check: a dead client must not keep time hostage ----------
def _janitor():
    while True:
        time.sleep(15)
        if DEV_OPEN:
            continue
        try:
            _evaluate()
        except Exception:
            pass


threading.Thread(target=_janitor, daemon=True).start()