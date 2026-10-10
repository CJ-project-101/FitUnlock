import json
import os
import sqlite3
import time
from datetime import datetime

MAX_BANK_SECONDS = 60 * 60

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_PATH = os.path.join(BASE_DIR, "shared", "session.json")
DB_PATH      = os.path.join(BASE_DIR, "shared", "fitplay.db")


# ── SQLite history ─────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity TEXT NOT NULL,
            reps_or_minutes TEXT NOT NULL,
            minutes_earned INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def log_session_to_db(activity, reps_or_minutes, minutes_earned):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (activity, reps_or_minutes, minutes_earned, timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        activity,
        str(reps_or_minutes),
        minutes_earned,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()


def get_session_history(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT activity, reps_or_minutes, minutes_earned, timestamp
        FROM sessions ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_total_minutes_today():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(minutes_earned) FROM sessions
        WHERE timestamp LIKE ?
    """, (f"{today}%",))
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0


# ── session.json ───────────────────────────────────────────────────────────
def _default_session():
    return {
        "banked_seconds": 0,
        "max_bank_seconds": MAX_BANK_SECONDS,
        "active_session": {
            "status": "locked",
            "seconds_remaining": 0,
            "started_at": ""
        }
    }


def _atomic_write_session(session_dict):
    """Write to a temp file, then swap it in. Retries if Unity has the file open."""
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    temp_path = SESSION_PATH + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(session_dict, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    for _ in range(10):
        try:
            os.replace(temp_path, SESSION_PATH)
            return
        except PermissionError:
            time.sleep(0.05)
    os.replace(temp_path, SESSION_PATH)   # last attempt, let it raise


def read_session():
    """
    Always returns a clean, seconds-based session dict.
    Legacy keys (banked_minutes, max_bank, ...) are dropped on the next write.
    """
    if not os.path.exists(SESSION_PATH):
        return _default_session()

    data = None
    for _ in range(5):
        try:
            with open(SESSION_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            break
        except (json.JSONDecodeError, OSError):
            time.sleep(0.05)      # Unity may be mid-write

    if not isinstance(data, dict):
        print("[session.py] session.json unreadable - using a clean default.")
        return _default_session()

    session = _default_session()

    try:
        bank = int(data.get("banked_seconds", 0))
    except (TypeError, ValueError):
        bank = 0
    session["banked_seconds"] = max(0, min(bank, MAX_BANK_SECONDS))

    active = data.get("active_session") or {}
    for key in ("status", "seconds_remaining", "started_at"):
        if key in active:
            session["active_session"][key] = active[key]

    return session


def add_minutes_to_bank(earned_minutes, activity=None, reps_or_minutes=""):
    """
    Adds earned time to the bank, capped at one hour.
    Pass `activity` to also log the session to SQLite.
    """
    earned_seconds = int(round(earned_minutes * 60))   # JSON must hold an int

    session = read_session()
    new_total = min(session["banked_seconds"] + earned_seconds, MAX_BANK_SECONDS)
    session["banked_seconds"] = new_total

    _atomic_write_session(session)

    if activity is not None:
        log_session_to_db(activity, reps_or_minutes, earned_minutes)

    print(f"[session.py] Banked {earned_seconds} sec. "
          f"Total: {new_total // 60} min {new_total % 60:02d} sec")
    return new_total


def get_banked_seconds():
    return read_session()["banked_seconds"]


def start_play_session(seconds_to_spend):
    """Moves time from the bank into an active, timestamped play session."""
    seconds_to_spend = int(seconds_to_spend)
    if seconds_to_spend <= 0:
        return False

    session = read_session()
    bank = session["banked_seconds"]

    if seconds_to_spend > bank:
        print(f"[session.py] Not enough time ({bank} seconds available).")
        return False

    session["banked_seconds"] = bank - seconds_to_spend
    session["active_session"] = {
        "status": "unlocked",
        "seconds_remaining": seconds_to_spend,
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    _atomic_write_session(session)
    print(f"[session.py] Play session: {seconds_to_spend} sec. "
          f"Bank left: {session['banked_seconds']} sec")
    return True


def lock_active_session():
    """Ends any active play session. The bank is never touched."""
    session = read_session()
    session["active_session"] = {
        "status": "locked",
        "seconds_remaining": 0,
        "started_at": ""
    }
    _atomic_write_session(session)
    print("[session.py] Active session locked. Bank preserved.")