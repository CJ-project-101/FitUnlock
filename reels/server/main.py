import os, uuid, hashlib, secrets, datetime as dt
from pathlib import Path

import cv2
import jwt
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
# CHANGED: removed the unused "from fastapi.staticfiles import StaticFiles" line
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, String, ForeignKey, DateTime, Text, func, select
from sqlalchemy.orm import (sessionmaker, DeclarativeBase, Mapped,
                            mapped_column, Session)
from starlette.concurrency import run_in_threadpool

from fastapi.responses import FileResponse
from gate import router as gate_router, require_unlocked

import numpy as np
import reelguard
from sqlalchemy import (create_engine, String, ForeignKey, DateTime, Text, func, select, inspect,
                        update, or_, and_, Float, Boolean, text as sql_text)

SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
DB_URL = os.getenv("DATABASE_URL", "sqlite:///reels.db")
MEDIA = Path("media"); MEDIA.mkdir(exist_ok=True)
ALLOWED = {".mp4", ".mov", ".webm", ".mkv"}
MAX_BYTES = 100 * 1024 * 1024

MAX_AVATAR = 3 * 1024 * 1024
AVATARS = MEDIA / "avatars"; AVATARS.mkdir(exist_ok=True)
ADMINS = {n.strip().lower() for n in os.getenv("REELGUARD_ADMINS", "").split(",") if n.strip()}
BLOCK_THREATS = os.getenv("REELGUARD_BLOCK_THREATS", "1") == "1"   # 1 = threats can never be posted

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(engine)
now = lambda: dt.datetime.now(dt.timezone.utc)

class Base(DeclarativeBase): pass

def make_thumb(video_path: Path, thumb_path: Path):
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_MSEC, 500)          # frame at 0.5 s
    ok, frame = cap.read()
    if not ok:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = cap.read()
    cap.release()
    if ok:
        h, w = frame.shape[:2]
        if w > 480:
            frame = cv2.resize(frame, (480, int(h * 480 / w)))
        cv2.imwrite(str(thumb_path), frame)

def thumb_url(filename: str):
    t = Path(filename).stem + ".jpg"
    return f"/media/{t}" if (MEDIA / t).exists() else None

class User(Base):
    __tablename__ = "reel_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)
    bio: Mapped[str] = mapped_column(String(160), default="")
    avatar: Mapped[str | None] = mapped_column(String(100), nullable=True)

class Reel(Base):
    __tablename__ = "reels"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(100))
    caption: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class Like(Base):
    __tablename__ = "likes"
    user_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), primary_key=True)
    reel_id: Mapped[int] = mapped_column(ForeignKey("reels.id"), primary_key=True)

class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    reel_id: Mapped[int] = mapped_column(ForeignKey("reels.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"))
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)
    label: Mapped[str] = mapped_column(String(12), default="safe")
    score: Mapped[float] = mapped_column(Float, default=0.0)

class Follow(Base):
    __tablename__ = "follows"
    follower_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), primary_key=True)
    followee_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), primary_key=True)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), index=True)
    text: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), index=True)     # who gets it
    actor_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"))                # who did it
    kind: Mapped[str] = mapped_column(String(12))                                     # like / comment / follow
    reel_id: Mapped[int | None] = mapped_column(nullable=True)
    detail: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)

class GuardLog(Base):
    __tablename__ = "guard_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), index=True)
    reel_id: Mapped[int] = mapped_column(default=0)
    text: Mapped[str] = mapped_column(String(500))
    label: Mapped[str] = mapped_column(String(12))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reasons: Mapped[str] = mapped_column(String(300), default="")
    outcome: Mapped[str] = mapped_column(String(24))   # published / flagged / blocked / held / published_after_review
    comment_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

Base.metadata.create_all(engine)

def ensure_columns():
    """create_all never changes existing tables, so add the new columns by hand."""
    insp = inspect(engine)
    wanted = {"reel_users": {"bio": "VARCHAR(160) DEFAULT ''", "avatar": "VARCHAR(100)"},
              "comments": {"label": "VARCHAR(12) DEFAULT 'safe'", "score": "FLOAT DEFAULT 0"}}
    with engine.begin() as conn:
        for table, cols in wanted.items():
            have = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name not in have:
                    conn.execute(sql_text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))

ensure_columns()

app = FastAPI(title="Reels API")

bearer = HTTPBearer()


app.include_router(gate_router)

@app.get("/media/{name}")
def media(name: str):
    """Thumbnails are public. Videos are served only while a session is unlocked."""
    p = (MEDIA / name).resolve()
    if p.parent != MEDIA.resolve() or not p.is_file():
        raise HTTPException(404, "Not found")
    if p.suffix.lower() != ".jpg":
        require_unlocked()
    return FileResponse(p)


def get_db():
    with SessionLocal() as db:
        yield db

def avatar_url(u):
    return f"/avatar/{u.avatar}" if u is not None and u.avatar else None

def iso(d):
    return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).isoformat()

def is_admin(u):
    return u.username in ADMINS or u.id == 1          # the first account is always a moderator

def notify(db, user_id, actor, kind, reel_id=None, detail=""):
    if user_id == actor.id:
        return
    if kind != "comment" and db.scalar(select(Notification.id).where(
            Notification.user_id == user_id, Notification.actor_id == actor.id,
            Notification.kind == kind, Notification.reel_id == reel_id, Notification.read.is_(False))):
        return                                          # no duplicate like/follow spam
    db.add(Notification(user_id=user_id, actor_id=actor.id, kind=kind, reel_id=reel_id, detail=detail[:120]))
    db.commit()

def log_guard(db, me, reel_id, text, v, outcome, comment_id=None):
    db.add(GuardLog(user_id=me.id, reel_id=reel_id, text=text[:500], label=v["label"], score=v["score"],
                    reasons="; ".join(v["reasons"])[:300], outcome=outcome, comment_id=comment_id))
    db.commit()

# ---------- auth ----------
def hash_pw(pw: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${h}"

def check_pw(pw: str, stored: str) -> bool:
    salt, _ = stored.split("$")
    return secrets.compare_digest(hash_pw(pw, salt), stored)

def make_token(uid: int) -> str:
    return jwt.encode({"sub": str(uid), "exp": now() + dt.timedelta(days=7)}, SECRET, "HS256")

def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer),
                 db: Session = Depends(get_db)) -> User:
    try:
        uid = int(jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, "Unknown user")
    return user

def require_admin(me: User = Depends(current_user)) -> User:
    if not is_admin(me):
        raise HTTPException(403, "Moderators only")
    return me

class Creds(BaseModel):
    username: str
    password: str

@app.post("/signup")
def signup(c: Creds, db: Session = Depends(get_db)):
    name = c.username.strip().lower()
    if not (3 <= len(name) <= 40) or len(c.password) < 6:
        raise HTTPException(400, "Username 3-40 chars, password at least 6")
    if db.scalar(select(User).where(User.username == name)):
        raise HTTPException(409, "Username taken")
    u = User(username=name, password_hash=hash_pw(c.password))
    db.add(u); db.commit()
    return {"token": make_token(u.id), "username": u.username}

@app.post("/login")
def login(c: Creds, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.username == c.username.strip().lower()))
    if not u or not check_pw(c.password, u.password_hash):
        raise HTTPException(401, "Wrong username or password")
    return {"token": make_token(u.id), "username": u.username}

# ---------- reels ----------
def reel_dict(db: Session, r: Reel, me: User) -> dict:
    author = db.get(User, r.user_id)
    likes = db.scalar(select(func.count()).select_from(Like).where(Like.reel_id == r.id))
    comments = db.scalar(select(func.count()).select_from(Comment).where(Comment.reel_id == r.id))
    liked = db.get(Like, (me.id, r.id)) is not None
    return {"id": r.id, "author": author.username, "author_avatar": avatar_url(author), "caption": r.caption,
            "video_url": f"/media/{r.filename}", "thumb_url": thumb_url(r.filename),
            "likes": likes, "comments": comments, "liked": liked}


# CHANGED: the feed is refused while Reels is locked
@app.get("/reels", dependencies=[Depends(require_unlocked)])
def feed(offset: int = 0, limit: int = 20, db: Session = Depends(get_db),
         me: User = Depends(current_user)):
    rows = db.scalars(select(Reel).order_by(Reel.created_at.desc())
                      .offset(offset).limit(min(limit, 50))).all()
    return [reel_dict(db, r, me) for r in rows]

@app.post("/reels")
async def upload(caption: str = Form(""), file: UploadFile = File(...),
                 db: Session = Depends(get_db), me: User = Depends(current_user)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, "Unsupported video type")
    name = f"{uuid.uuid4().hex}{ext}"
    size = 0
    with open(MEDIA / name, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                out.close(); (MEDIA / name).unlink(missing_ok=True)
                raise HTTPException(413, "File too large (100 MB max)")
            out.write(chunk)
    # CHANGED: moved out of the "with" block, so the file is fully written and closed first
    await run_in_threadpool(make_thumb, MEDIA / name, MEDIA / (Path(name).stem + ".jpg"))
    r = Reel(user_id=me.id, filename=name, caption=caption[:300])
    db.add(r); db.commit()
    return reel_dict(db, r, me)

@app.post("/reels/{rid}/like")
def like(rid: int, db: Session = Depends(get_db), me: User = Depends(current_user)):
    reel = db.get(Reel, rid)
    if not reel: raise HTTPException(404, "No such reel")
    if not db.get(Like, (me.id, rid)):
        db.add(Like(user_id=me.id, reel_id=rid)); db.commit()
        notify(db, reel.user_id, me, "like", rid)
    return {"ok": True}

@app.delete("/reels/{rid}/like")
def unlike(rid: int, db: Session = Depends(get_db), me: User = Depends(current_user)):
    l = db.get(Like, (me.id, rid))
    if l: db.delete(l); db.commit()
    return {"ok": True}

# ---------- comments ----------
class NewComment(BaseModel):
    text: str
    confirmed: bool = False

@app.get("/reels/{rid}/comments")
def comments(rid: int, db: Session = Depends(get_db), me: User = Depends(current_user)):
    rows = db.scalars(select(Comment).where(Comment.reel_id == rid)
                      .order_by(Comment.created_at.desc()).limit(100)).all()
    out = []
    for c in rows:
        u = db.get(User, c.user_id)
        out.append({"author": u.username, "text": c.text, "avatar_url": avatar_url(u)})
    return out

@app.post("/reels/{rid}/comments")
def add_comment(rid: int, body: NewComment, db: Session = Depends(get_db), me: User = Depends(current_user)):
    text = body.text.strip()
    if not text: raise HTTPException(400, "Empty comment")
    reel = db.get(Reel, rid)
    if not reel: raise HTTPException(404, "No such reel")
    v = reelguard.classify(text)                         # the server never trusts the client's check
    if v["label"] == "threatening" and BLOCK_THREATS:
        log_guard(db, me, rid, text, v, "blocked")
        raise HTTPException(422, "ReelGuard blocked this comment because it looks like a threat.")
    if v["label"] == "abusive" and not body.confirmed:
        log_guard(db, me, rid, text, v, "held")
        raise HTTPException(409, "ReelGuard: this comment may be abusive. Review it before posting.")
    c = Comment(reel_id=rid, user_id=me.id, text=text[:500], label=v["label"], score=v["score"])
    db.add(c); db.commit()
    log_guard(db, me, rid, text, v, "published" if v["label"] == "safe" else "published_after_review", c.id)
    notify(db, reel.user_id, me, "comment", rid, text)
    return {"ok": True}

# ---------- profiles / follow ----------
def find_user(db: Session, username: str) -> User:
    u = db.scalar(select(User).where(User.username == username.lower()))
    if not u: raise HTTPException(404, "No such user")
    return u

@app.get("/users/{username}")
def profile(username: str, db: Session = Depends(get_db), me: User = Depends(current_user)):
    u = find_user(db, username)
    count = lambda q: db.scalar(select(func.count()).select_from(q))
    reels = db.scalars(select(Reel).where(Reel.user_id == u.id)
                       .order_by(Reel.created_at.desc())).all()
    return {"username": u.username,
            "bio": u.bio or "", 
            "avatar_url": avatar_url(u),
            "followers": db.scalar(select(func.count()).select_from(Follow).where(Follow.followee_id == u.id)),
            "following": db.scalar(select(func.count()).select_from(Follow).where(Follow.follower_id == u.id)),
            "is_me": u.id == me.id,
            "i_follow": db.get(Follow, (me.id, u.id)) is not None,
            "reels": [{"id": r.id, "caption": r.caption, "thumb_url": thumb_url(r.filename)}
                      for r in reels]}

@app.get("/users/{username}/reels", dependencies=[Depends(require_unlocked)])
def user_reels(username: str, db: Session = Depends(get_db), me: User = Depends(current_user)):
    u = find_user(db, username)
    rows = db.scalars(select(Reel).where(Reel.user_id == u.id)
                      .order_by(Reel.created_at.desc()).limit(100)).all()
    return [reel_dict(db, r, me) for r in rows]

@app.post("/follow/{username}")
def follow(username: str, db: Session = Depends(get_db), me: User = Depends(current_user)):
    u = find_user(db, username)
    if u.id == me.id: raise HTTPException(400, "Can't follow yourself")
    if not db.get(Follow, (me.id, u.id)):
        db.add(Follow(follower_id=me.id, followee_id=u.id)); db.commit()
        notify(db, u.id, me, "follow")
    return {"ok": True}

@app.delete("/follow/{username}")
def unfollow(username: str, db: Session = Depends(get_db), me: User = Depends(current_user)):
    u = find_user(db, username)
    f = db.get(Follow, (me.id, u.id))
    if f: db.delete(f); db.commit()
    return {"ok": True}


# ---------- profile picture + bio ----------
@app.get("/avatar/{name}")
def avatar_file(name: str):
    p = (AVATARS / name).resolve()
    if p.parent != AVATARS.resolve() or not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p)

class ProfileEdit(BaseModel):
    bio: str = ""

@app.get("/me")
def me_info(me: User = Depends(current_user)):
    return {"username": me.username, "bio": me.bio or "", "avatar_url": avatar_url(me), "is_admin": is_admin(me)}

@app.put("/me")
def edit_me(body: ProfileEdit, db: Session = Depends(get_db), me: User = Depends(current_user)):
    me.bio = body.bio.strip()[:150]
    db.commit()
    return {"ok": True}

@app.post("/me/avatar")
async def set_avatar(file: UploadFile = File(...), db: Session = Depends(get_db), me: User = Depends(current_user)):
    data = await file.read(MAX_AVATAR + 1)
    if len(data) > MAX_AVATAR: raise HTTPException(413, "Image too large (3 MB max)")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None: raise HTTPException(400, "That file is not a valid image")
    h, w = img.shape[:2]; s = min(h, w)
    img = img[(h - s) // 2:(h - s) // 2 + s, (w - s) // 2:(w - s) // 2 + s]          # centre square
    img = cv2.resize(img, (256, 256), interpolation=cv2.INTER_AREA)
    mask = np.zeros((256, 256), np.uint8)
    cv2.circle(mask, (128, 128), 127, 255, -1, cv2.LINE_AA)                         # round the corners
    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA); img[:, :, 3] = mask
    name = f"{uuid.uuid4().hex}.png"
    cv2.imwrite(str(AVATARS / name), img)
    if me.avatar: (AVATARS / me.avatar).unlink(missing_ok=True)
    me.avatar = name; db.commit()
    return {"avatar_url": avatar_url(me)}

# ---------- notifications ----------
@app.get("/notifications")
def notifications(db: Session = Depends(get_db), me: User = Depends(current_user)):
    rows = db.scalars(select(Notification).where(Notification.user_id == me.id)
                      .order_by(Notification.created_at.desc()).limit(60)).all()
    out = []
    for n in rows:
        a = db.get(User, n.actor_id)
        out.append({"nid": n.id, "kind": n.kind, "actor": a.username, "avatar_url": avatar_url(a),
                    "reel_id": n.reel_id or 0, "detail": n.detail or "", "read": bool(n.read),
                    "created_at": iso(n.created_at)})
    return out

@app.post("/notifications/read")
def notifications_read(db: Session = Depends(get_db), me: User = Depends(current_user)):
    db.execute(update(Notification).where(Notification.user_id == me.id, Notification.read.is_(False)).values(read=True))
    db.commit()
    return {"ok": True}

@app.get("/activity")
def activity(db: Session = Depends(get_db), me: User = Depends(current_user)):
    n = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == me.id, Notification.read.is_(False)))
    m = db.scalar(select(func.count()).select_from(Message).where(Message.recipient_id == me.id, Message.read.is_(False)))
    return {"notifications": n, "messages": m}

# ---------- direct messages ----------
class NewMessage(BaseModel):
    text: str

@app.get("/messages")
def conversations(db: Session = Depends(get_db), me: User = Depends(current_user)):
    rows = db.scalars(select(Message).where(or_(Message.sender_id == me.id, Message.recipient_id == me.id))
                      .order_by(Message.created_at.desc()).limit(500)).all()
    seen = {}
    for m in rows:
        other = m.recipient_id if m.sender_id == me.id else m.sender_id
        c = seen.setdefault(other, {"last": m, "unread": 0})
        if m.recipient_id == me.id and not m.read:
            c["unread"] += 1
    out = []
    for oid, c in seen.items():                       # newest conversation first
        u = db.get(User, oid)
        out.append({"username": u.username, "avatar_url": avatar_url(u) or "", "last": c["last"].text,
                    "mine": c["last"].sender_id == me.id, "time": iso(c["last"].created_at), "unread": c["unread"]})
    return out

@app.get("/messages/{username}")
def thread(username: str, db: Session = Depends(get_db), me: User = Depends(current_user)):
    u = find_user(db, username)
    rows = db.scalars(select(Message).where(or_(
        and_(Message.sender_id == me.id, Message.recipient_id == u.id),
        and_(Message.sender_id == u.id, Message.recipient_id == me.id)))
        .order_by(Message.created_at.desc()).limit(100)).all()
    rows.reverse()
    db.execute(update(Message).where(Message.sender_id == u.id, Message.recipient_id == me.id,
                                     Message.read.is_(False)).values(read=True))
    db.commit()
    return {"user": {"username": u.username, "avatar_url": avatar_url(u) or ""},
            "messages": [{"mid": m.id, "mine": m.sender_id == me.id, "text": m.text, "time": iso(m.created_at)} for m in rows]}

@app.post("/messages/{username}")
def send_message(username: str, body: NewMessage, db: Session = Depends(get_db), me: User = Depends(current_user)):
    u = find_user(db, username)
    t = body.text.strip()
    if u.id == me.id: raise HTTPException(400, "You can't message yourself")
    if not t: raise HTTPException(400, "Empty message")
    db.add(Message(sender_id=me.id, recipient_id=u.id, text=t[:1000])); db.commit()
    return {"ok": True}

# ---------- ReelGuard ----------
class CheckBody(BaseModel):
    reel_id: int = 0
    text: str

@app.post("/comments/check")
def comment_check(body: CheckBody, db: Session = Depends(get_db), me: User = Depends(current_user)):
    v = reelguard.classify(body.text)
    blocked = v["label"] == "threatening" and BLOCK_THREATS
    if v["label"] != "safe":
        log_guard(db, me, body.reel_id, body.text, v, "blocked" if blocked else "flagged")
    return {**v, "blocked": blocked}

@app.get("/moderation/summary")
def mod_summary(db: Session = Depends(get_db), me: User = Depends(require_admin)):
    rows = db.execute(select(GuardLog.label, GuardLog.outcome, func.count()).group_by(GuardLog.label, GuardLog.outcome)).all()
    classified = {"safe": 0, "abusive": 0, "threatening": 0}
    out = {"after_review": 0, "blocked": 0, "flagged": 0}
    for label, outcome, n in rows:
        if outcome == "published_after_review":
            out["after_review"] += n                   # a follow-up to a flag, so not counted twice
            continue
        classified[label] = classified.get(label, 0) + n
        if outcome == "blocked": out["blocked"] += n
        if outcome in ("flagged", "held"): out["flagged"] += n
    return {"classified": classified, "total": sum(classified.values()), **out, "engine": reelguard.status()}

@app.get("/moderation/log")
def mod_log(label: str = "", limit: int = 80, db: Session = Depends(get_db), me: User = Depends(require_admin)):
    q = select(GuardLog)
    if label: q = q.where(GuardLog.label == label)
    out = []
    for g in db.scalars(q.order_by(GuardLog.created_at.desc()).limit(min(limit, 200))).all():
        u = db.get(User, g.user_id)
        out.append({"gid": g.id, "user": u.username if u else "?", "reel_id": g.reel_id, "text": g.text,
                    "label": g.label, "score": g.score, "reasons": g.reasons or "", "outcome": g.outcome,
                    "time": iso(g.created_at), "comment_id": g.comment_id or 0,
                    "removed": bool(g.comment_id) and db.get(Comment, g.comment_id) is None})
    return out

@app.delete("/moderation/comments/{cid}")
def mod_remove(cid: int, db: Session = Depends(get_db), me: User = Depends(require_admin)):
    c = db.get(Comment, cid)
    if not c: raise HTTPException(404, "No such comment")
    db.delete(c); db.commit()
    return {"ok": True}


# CHANGED: the old placeholder /gate route was deleted from here.
# The real /gate, /gate/tick and /gate/end now live in gate.py.