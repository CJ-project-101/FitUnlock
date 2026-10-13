
"""
FitPlay cloud layer, built on Firebase's REST APIs (only the `requests` package).
 
Why REST instead of firebase-admin:
  * firebase-admin pulls in a protobuf version that breaks MediaPipe 0.10.9.
  * The admin credentials file no longer has to ship inside the desktop app.
    Everything here runs as the signed-in user and is limited by Firestore
    security rules.
 
Public functions (unchanged names, so the UI files need no edits):
    init_firebase, create_user, verify_login_rest, restore_session, clear_session,
    update_leaderboard_stats, get_leaderboard
"""
import json
import os
import threading
import time
 
import requests
 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_PATH = os.path.join(BASE_DIR, "shared", "auth_session.json")   # "stay signed in" file
 
# Firebase Console > Project settings > General
WEB_API_KEY = "AIzaSyCbTCYCNXxOs7QF3eUbnlv8-kszM1TPnBc"     # "Web API Key"
PROJECT_ID = "fitplay-468b4"     # "Project ID"
 
TIMEOUT = 10
NETWORK_MSG = "Can't reach the server. Check your internet connection."
 
_AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts"
_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
_FS_ROOT = "https://firestore.googleapis.com/v1"
 
FRIENDLY_ERRORS = {
    "EMAIL_EXISTS": "An account with this email already exists.",
    "INVALID_LOGIN_CREDENTIALS": "Wrong email or password.",
    "EMAIL_NOT_FOUND": "Wrong email or password.",
    "INVALID_PASSWORD": "Wrong email or password.",
    "INVALID_EMAIL": "That email address isn't valid.",
    "MISSING_PASSWORD": "Please enter a password.",
    "WEAK_PASSWORD": "Password must be at least 6 characters.",
    "USER_DISABLED": "This account has been disabled.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Try again in a few minutes.",
    "OPERATION_NOT_ALLOWED": "Email/Password sign-in isn't enabled in Firebase.",
    "API_KEY_INVALID": "The Web API Key in auth.py is not valid.",
}
 
# Who is signed in right now, plus the short-lived token Firestore needs.
_state = {"uid": None, "email": None, "id_token": None,
          "refresh_token": None, "expires_at": 0}
_lock = threading.Lock()
 
 
# ─────────────────────────────────────────────────────────────
# SETUP CHECK
# ─────────────────────────────────────────────────────────────
 
def init_firebase():
    """Called at startup. Only checks that the two settings above were filled in."""
    if "PASTE_" in WEB_API_KEY or "PASTE_" in PROJECT_ID:
        raise RuntimeError(
            "Open python_app/auth.py and set WEB_API_KEY and PROJECT_ID "
            "(Firebase Console > Project settings > General).")
    return True
 
 
def _doc_root():
    return f"projects/{PROJECT_ID}/databases/(default)/documents"
 
 
def _headers(token):
    return {"Authorization": f"Bearer {token}"}
 
 
def _firebase_error(resp):
    try:
        raw = resp.json().get("error", {}).get("message", "")
    except ValueError:
        raw = ""
    code = raw.split(" ")[0] if raw else ""
    return FRIENDLY_ERRORS.get(code, raw or f"Request failed ({resp.status_code})")
 
 
# Firestore value helpers
def _s(value):
    return {"stringValue": str(value)}
 
 
def _i(value):
    return {"integerValue": str(int(value))}
 
 
def _as_int(value):
    if not value:
        return 0
    for key in ("integerValue", "doubleValue"):
        if key in value:
            try:
                return int(float(value[key]))
            except (TypeError, ValueError):
                return 0
    return 0
 
 
# ─────────────────────────────────────────────────────────────
# SAVED SESSION  ("stay signed in" + logout)
# ─────────────────────────────────────────────────────────────
 
def _save_session(uid, email, refresh_token):
    try:
        os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
        with open(SESSION_PATH, "w", encoding="utf-8") as f:
            json.dump({"uid": uid, "email": email, "refresh_token": refresh_token}, f)
    except OSError as e:
        print(f"[auth] could not save session: {e}")
 
 
def _load_session():
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("uid") and data.get("refresh_token"):
            return data
    except (OSError, ValueError):
        pass
    return None
 
 
def clear_session():
    """Logout: forget the saved login on this machine and in memory."""
    _state.update(uid=None, email=None, id_token=None, refresh_token=None, expires_at=0)
    try:
        os.remove(SESSION_PATH)
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f"[auth] could not clear session: {e}")
 
 
def _remember(uid, email, id_token, refresh_token, expires_in):
    _state.update(uid=uid, email=email, id_token=id_token,
                  refresh_token=refresh_token,
                  expires_at=time.time() + int(expires_in))
    _save_session(uid, email, refresh_token)
 
 
def _refresh(refresh_token, timeout=TIMEOUT):
    """Trades a refresh token for a fresh ID token.
    Returns (kind, body) where kind is 'ok', 'offline' or 'rejected'."""
    if not refresh_token:
        return "rejected", None
    try:
        resp = requests.post(
            f"{_TOKEN_URL}?key={WEB_API_KEY}",
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=timeout)
    except requests.RequestException:
        return "offline", None
    if resp.status_code == 200:
        return "ok", resp.json()
    if resp.status_code in (400, 401, 403):
        return "rejected", None          # account deleted/disabled or sessions revoked
    return "offline", None               # server trouble: treat like no connection
 
 
def _get_id_token():
    """A valid ID token for Firestore calls, refreshed when it is about to expire."""
    with _lock:
        if _state["id_token"] and time.time() < _state["expires_at"] - 60:
            return _state["id_token"]
        kind, body = _refresh(_state["refresh_token"])
        if kind == "ok":
            _remember(body["user_id"], _state.get("email") or "", body["id_token"],
                      body.get("refresh_token", _state["refresh_token"]),
                      body.get("expires_in", 3600))
            return body["id_token"]
        return None
 
 
def restore_session():
    """Returns (uid, email) if a saved login exists and is still valid, else None.
    If the network is down, the saved login is trusted so the app still opens offline."""
    data = _load_session()
    if not data:
        return None
 
    _state.update(uid=data["uid"], email=data.get("email", ""),
                  refresh_token=data["refresh_token"], id_token=None, expires_at=0)
 
    kind, body = _refresh(data["refresh_token"], timeout=5)
    if kind == "ok":
        _remember(body.get("user_id", data["uid"]), data.get("email", ""),
                  body["id_token"], body.get("refresh_token", data["refresh_token"]),
                  body.get("expires_in", 3600))
        return _state["uid"], _state["email"]
    if kind == "offline":
        return data["uid"], data.get("email", "")
 
    clear_session()
    return None
 
 
# ─────────────────────────────────────────────────────────────
# ACCOUNTS
# ─────────────────────────────────────────────────────────────
 
def create_user(email, password, display_name):
    """Sign up a new user and create their leaderboard profile. Returns (ok, uid_or_error).
    Does not sign the user in; the login screen takes them to the login form afterwards."""
    try:
        resp = requests.post(f"{_AUTH_URL}:signUp?key={WEB_API_KEY}",
                             json={"email": email, "password": password,
                                   "returnSecureToken": True},
                             timeout=TIMEOUT)
    except requests.RequestException:
        return False, NETWORK_MSG
 
    if resp.status_code != 200:
        return False, _firebase_error(resp)
 
    body = resp.json()
    uid, id_token = body["localId"], body["idToken"]
 
    # Display name on the Auth record (best effort; the Firestore profile is what the app reads)
    try:
        requests.post(f"{_AUTH_URL}:update?key={WEB_API_KEY}",
                      json={"idToken": id_token, "displayName": display_name,
                            "returnSecureToken": False},
                      timeout=TIMEOUT)
    except requests.RequestException:
        pass
 
    # Leaderboard profile document: users/<uid>
    fields = {
        "display_name": _s(display_name),
        "email": _s(email),
        "total_exercise_minutes": _i(0),
        "total_sessions": _i(0),
        "squats_total": _i(0),
        "push_ups_total": _i(0),
        "jumping_jacks_total": _i(0),
        "walking_total": _i(0),
    }
    try:
        doc = requests.patch(f"{_FS_ROOT}/{_doc_root()}/users/{uid}",
                             json={"fields": fields},
                             headers=_headers(id_token), timeout=TIMEOUT)
    except requests.RequestException:
        return False, "Account created, but the profile could not be saved (no connection)."
 
    if doc.status_code != 200:
        print(f"[auth] profile write failed: {doc.status_code} {doc.text[:300]}")
        return False, ("Account created, but profile setup failed. "
                       "Check your Firestore security rules.")
    return True, uid
 
 
def verify_login_rest(email, password):
    """Check email + password. Returns (ok, uid_or_error).
    On success the login is saved so the app stays signed in next time."""
    try:
        resp = requests.post(f"{_AUTH_URL}:signInWithPassword?key={WEB_API_KEY}",
                             json={"email": email, "password": password,
                                   "returnSecureToken": True},
                             timeout=TIMEOUT)
    except requests.RequestException:
        return False, NETWORK_MSG
 
    if resp.status_code == 200:
        data = resp.json()
        _remember(data["localId"], data.get("email", email), data["idToken"],
                  data.get("refreshToken", ""), data.get("expiresIn", 3600))
        return True, data["localId"]
 
    return False, _firebase_error(resp)
 
 
# ─────────────────────────────────────────────────────────────
# LEADERBOARD  (Firestore REST)
# ─────────────────────────────────────────────────────────────
 
def update_leaderboard_stats(uid, activity_name, minutes_earned):
    """Call whenever a user completes an exercise. Never raises, so a network blip
    can't crash the exercise flow. Uses server-side increments, so concurrent
    updates don't overwrite each other."""
    token = _get_id_token()
    if not token:
        print("[leaderboard] update skipped: not signed in or offline")
        return False
 
    body = {"writes": [{
        "update": {"name": f"{_doc_root()}/users/{uid}"},
        "updateMask": {"fieldPaths": []},          # create the doc if missing, touch nothing else
        "updateTransforms": [
            {"fieldPath": "total_exercise_minutes", "increment": _i(minutes_earned)},
            {"fieldPath": "total_sessions", "increment": _i(1)},
            {"fieldPath": f"{activity_name}_total", "increment": _i(1)},
        ],
    }]}
    try:
        resp = requests.post(f"{_FS_ROOT}/{_doc_root()}:commit", json=body,
                             headers=_headers(token), timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"[leaderboard] update failed: {e}")
        return False
 
    if resp.status_code != 200:
        print(f"[leaderboard] update rejected: {resp.status_code} {resp.text[:300]}")
        return False
    return True
 
 
def get_leaderboard(limit=10):
    """Top users by total exercise minutes."""
    token = _get_id_token()
    if not token:
        return []
 
    body = {"structuredQuery": {
        "from": [{"collectionId": "users"}],
        "orderBy": [{"field": {"fieldPath": "total_exercise_minutes"},
                     "direction": "DESCENDING"}],
        "limit": int(limit),
    }}
    try:
        resp = requests.post(f"{_FS_ROOT}/{_doc_root()}:runQuery", json=body,
                             headers=_headers(token), timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"[leaderboard] fetch failed: {e}")
        return []
 
    if resp.status_code != 200:
        print(f"[leaderboard] fetch rejected: {resp.status_code} {resp.text[:300]}")
        return []
 
    results = []
    for item in resp.json():
        doc = item.get("document")
        if not doc:                       # an empty result set returns one entry with no document
            continue
        fields = doc.get("fields", {})
        results.append({
            "uid": doc["name"].rsplit("/", 1)[-1],
            "name": fields.get("display_name", {}).get("stringValue", "Unknown"),
            "minutes": _as_int(fields.get("total_exercise_minutes")),
            "sessions": _as_int(fields.get("total_sessions")),
        })
    return results
 

