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
    def add_comment(self, rid, t):  return self._call("POST", f"/reels/{rid}/comments", json={"text": t})
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