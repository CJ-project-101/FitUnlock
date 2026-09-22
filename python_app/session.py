import json
import os
import sqlite3
from datetime import datetime


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


def write_session(minutes_earned, activity, reps_or_minutes):
    """
    Called after a successful exercise.
    Unlocks the game by writing minutes_earned to session.json,
    and logs the session to the database.
    """
    session = {
        "status": "unlocked",
        "minutes_earned": minutes_earned,
        "activity_done": activity,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    _atomic_write_session(session)

    log_session_to_db(
        activity,
        reps_or_minutes,
        minutes_earned
    )

    print(
        f"[session.py] Wrote session: "
        f"{activity} → {minutes_earned} min"
    )

def lock_session():
    """Resets session.json to locked state — call this on app startup."""
    session = {
        "status": "locked",
        "minutes_earned": 0,
        "activity_done": "",
        "timestamp": ""
    }

    _atomic_write_session(session)

    print("[session.py] Session locked.")

def read_session():
    """Reads current session.json — mainly useful for debugging from Python side."""
    if not os.path.exists(SESSION_PATH):
        return None
    with open(SESSION_PATH, 'r') as f:
        return json.load(f)


# ── Quick manual test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing session.py...\n")

    init_db()

    print("1. Locking session...")
    lock_session()
    print("   Current state:", read_session())

    print("\n2. Simulating a completed squat session...")
    write_session(minutes_earned=15, activity="squats", reps_or_minutes=10)
    print("   Current state:", read_session())

    print("\n3. Session history from database:")
    for row in get_session_history():
        print("   ", row)

    print("\n4. Total minutes earned today:", get_total_minutes_today())

    print("\nAll tests done. Check shared/session.json and shared/fitplay.db")