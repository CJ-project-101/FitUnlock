import json
import os
import sqlite3
from datetime import datetime

MAX_BANK_SECONDS = 60 * 60

# ── Paths ──────────────────────────────────────────────────────────────────
# session.json lives in the shared/ folder so both Python and Unity can find it
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # FitPlay/
SESSION_PATH = os.path.join(BASE_DIR, "shared", "session.json")
DB_PATH      = os.path.join(BASE_DIR, "shared", "fitplay.db")


# ── SQLite setup ───────────────────────────────────────────────────────────
def init_db():
    """Creates the sessions table if it doesn't already exist."""
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
    """Adds one row to the history table."""
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
    """Returns the most recent sessions — useful for a stats screen later."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT activity, reps_or_minutes, minutes_earned, timestamp
        FROM sessions
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_total_minutes_today():
    """Returns total minutes earned today — nice for a dashboard stat."""
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


# ── session.json read/write ───────────────────────────────────────────────
def _atomic_write_session(session_dict):
    """
    Shared helper — writes session_dict to session.json safely.
    Writes to a temp file first, then atomically replaces the real file,
    so Unity (or anything else polling) can never read a half-written
    or empty session.json mid-write.
    """
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)

    temp_path = SESSION_PATH + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(session_dict, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_path, SESSION_PATH)

MAX_BANK_MINUTES = 60


def read_session():
    if not os.path.exists(SESSION_PATH):
        return {
            "banked_minutes": 0,
            "max_bank": MAX_BANK_MINUTES,
            "active_session": {
                "status": "locked",
                "minutes_remaining": 0,
                "started_at": ""
            }
        }

    with open(SESSION_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def add_minutes_to_bank(earned_minutes):
    session = read_session()

    current = session.get("banked_seconds", 0)
    earned_seconds = earned_minutes * 60

    new_total = min(
        current + earned_seconds,
        MAX_BANK_SECONDS
    )

    session["banked_seconds"] = new_total

    if "active_session" not in session:
        session["active_session"] = {
            "status": "locked",
            "seconds_remaining": 0,
            "started_at": ""
        }

    _atomic_write_session(session)

    print(
        f"[session.py] Banked {earned_minutes} min. "
        f"Total: {new_total // 60} min "
        f"{new_total % 60:02d} sec"
    )

    return new_total


def get_banked_seconds():
    return read_session().get("banked_seconds", 0)


def start_play_session(seconds_to_spend):
    session = read_session()

    current_bank = session.get("banked_seconds", 0)

    if seconds_to_spend > current_bank:
        print(
            f"[session.py] Not enough time "
            f"({current_bank} seconds available)."
        )
        return False

    session["banked_seconds"] = current_bank - seconds_to_spend

    session["active_session"] = {
        "status": "unlocked",
        "seconds_remaining": seconds_to_spend,
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    _atomic_write_session(session)

    print(
        f"[session.py] Started play session: "
        f"{seconds_to_spend} seconds. "
        f"Remaining bank: {session['banked_seconds']} seconds"
    )

    return True


def lock_active_session():
    session = read_session()

    session["active_session"] = {
        "status": "locked",
        "seconds_remaining": 0,
        "started_at": ""
    }

    session["max_bank"] = MAX_BANK_MINUTES

    _atomic_write_session(session)

    print("[session.py] Active session locked. Bank preserved.")

