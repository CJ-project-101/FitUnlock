import requests

BASE = "http://127.0.0.1:8000"

class Api:

    def user_reels(self, name):
        return self._call("GET", f"/users/{name}/reels")

    def get_bytes(self, path):
        try:
            r = self.s.get(BASE + path, timeout=10)
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            return None

    def __init__(self):
        self.token = None
        self.username = None
        self.s = requests.Session()

    def _call(self, method, path, timeout=10, **kw):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            r = self.s.request(method, BASE + path, headers=headers, timeout=timeout, **kw)
        except requests.RequestException as e:
            raise RuntimeError(f"Can't reach server: {e}")
        if not r.ok:
            try: msg = r.json().get("detail", r.text)
            except Exception: msg = r.text
            raise RuntimeError(str(msg))
        return r.json()

    def auth(self, mode, username, password):          # mode: "login" or "signup"
        d = self._call("POST", f"/{mode}", json={"username": username, "password": password})
        self.token, self.username = d["token"], d["username"]

    def feed(self, offset=0, limit=20):
        return self._call("GET", "/reels", params={"offset": offset, "limit": limit})
    def like(self, rid, on):        return self._call("POST" if on else "DELETE", f"/reels/{rid}/like")
    def comments(self, rid):        return self._call("GET", f"/reels/{rid}/comments")
    def add_comment(self, rid, t, confirmed=False):
        return self._call("POST", f"/reels/{rid}/comments", json={"text": t, "confirmed": confirmed})
    def check_comment(self, rid, t):  return self._call("POST", "/comments/check", json={"reel_id": rid, "text": t})
    def me(self):                     return self._call("GET", "/me")
    def save_bio(self, bio):          return self._call("PUT", "/me", json={"bio": bio})
    def upload_avatar(self, path):
        with open(path, "rb") as f:
            return self._call("POST", "/me/avatar", timeout=30, files={"file": f})
    def activity(self):               return self._call("GET", "/activity", timeout=4)
    def notifications(self):          return self._call("GET", "/notifications")
    def notifications_read(self):     return self._call("POST", "/notifications/read")
    def conversations(self):          return self._call("GET", "/messages")
    def thread(self, name):           return self._call("GET", f"/messages/{name}")
    def send_message(self, name, t):  return self._call("POST", f"/messages/{name}", json={"text": t})
    def mod_summary(self):            return self._call("GET", "/moderation/summary")
    def mod_log(self, label=""):      return self._call("GET", "/moderation/log", params={"label": label})
    def mod_remove(self, cid):        return self._call("DELETE", f"/moderation/comments/{cid}")
    def profile(self, name):        return self._call("GET", f"/users/{name}")
    def follow(self, name, on):     return self._call("POST" if on else "DELETE", f"/follow/{name}")
    def gate(self):                 return self._call("GET", "/gate", timeout=3)

    def upload(self, path, caption):
        with open(path, "rb") as f:
            return self._call("POST", "/reels", timeout=120,
                              data={"caption": caption}, files={"file": f})

    def tick(self, watching):
        return self._call("POST", "/gate/tick", json={"watching": bool(watching)}, timeout=3)

    def gate_end(self):
        return self._call("POST", "/gate/end", timeout=3)