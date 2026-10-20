import os, uuid, hashlib, secrets, datetime as dt
from pathlib import Path

import cv2
import jwt
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, String, ForeignKey, DateTime, Text, func, select
from sqlalchemy.orm import (sessionmaker, DeclarativeBase, Mapped,
                            mapped_column, Session)
from starlette.concurrency import run_in_threadpool

SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
DB_URL = os.getenv("DATABASE_URL", "sqlite:///reels.db")
MEDIA = Path("media"); MEDIA.mkdir(exist_ok=True)
ALLOWED = {".mp4", ".mov", ".webm", ".mkv"}
MAX_BYTES = 100 * 1024 * 1024

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

class Follow(Base):
    __tablename__ = "follows"
    follower_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), primary_key=True)
    followee_id: Mapped[int] = mapped_column(ForeignKey("reel_users.id"), primary_key=True)

Base.metadata.create_all(engine)

app = FastAPI(title="Reels API")
app.mount("/media", StaticFiles(directory=MEDIA), name="media")
bearer = HTTPBearer()

def get_db():
    with SessionLocal() as db:
        yield db

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
    return {"id": r.id, "author": author.username, "caption": r.caption,
            "video_url": f"/media/{r.filename}", "thumb_url": thumb_url(r.filename),
            "likes": likes, "comments": comments, "liked": liked}


@app.get("/reels")
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
        await run_in_threadpool(make_thumb, MEDIA / name, MEDIA / (Path(name).stem + ".jpg"))
    r = Reel(user_id=me.id, filename=name, caption=caption[:300])
    db.add(r); db.commit()
    return reel_dict(db, r, me)

@app.post("/reels/{rid}/like")
def like(rid: int, db: Session = Depends(get_db), me: User = Depends(current_user)):
    if not db.get(Reel, rid): raise HTTPException(404, "No such reel")
    if not db.get(Like, (me.id, rid)):
        db.add(Like(user_id=me.id, reel_id=rid)); db.commit()
    return {"ok": True}

@app.delete("/reels/{rid}/like")
def unlike(rid: int, db: Session = Depends(get_db), me: User = Depends(current_user)):
    l = db.get(Like, (me.id, rid))
    if l: db.delete(l); db.commit()
    return {"ok": True}

# ---------- comments ----------
class NewComment(BaseModel):
    text: str

@app.get("/reels/{rid}/comments")
def comments(rid: int, db: Session = Depends(get_db), me: User = Depends(current_user)):
    rows = db.scalars(select(Comment).where(Comment.reel_id == rid)
                      .order_by(Comment.created_at.desc()).limit(100)).all()
    return [{"author": db.get(User, c.user_id).username, "text": c.text} for c in rows]

@app.post("/reels/{rid}/comments")
def add_comment(rid: int, body: NewComment, db: Session = Depends(get_db),
                me: User = Depends(current_user)):
    text = body.text.strip()
    if not text: raise HTTPException(400, "Empty comment")
    if not db.get(Reel, rid): raise HTTPException(404, "No such reel")
    db.add(Comment(reel_id=rid, user_id=me.id, text=text[:500])); db.commit()
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
            "followers": db.scalar(select(func.count()).select_from(Follow).where(Follow.followee_id == u.id)),
            "following": db.scalar(select(func.count()).select_from(Follow).where(Follow.follower_id == u.id)),
            "is_me": u.id == me.id,
            "i_follow": db.get(Follow, (me.id, u.id)) is not None,
            "reels": [{"id": r.id, "caption": r.caption, "thumb_url": thumb_url(r.filename)}
                      for r in reels]}

@app.post("/follow/{username}")
def follow(username: str, db: Session = Depends(get_db), me: User = Depends(current_user)):
    u = find_user(db, username)
    if u.id == me.id: raise HTTPException(400, "Can't follow yourself")
    if not db.get(Follow, (me.id, u.id)):
        db.add(Follow(follower_id=me.id, followee_id=u.id)); db.commit()
    return {"ok": True}

@app.delete("/follow/{username}")
def unfollow(username: str, db: Session = Depends(get_db), me: User = Depends(current_user)):
    u = find_user(db, username)
    f = db.get(Follow, (me.id, u.id))
    if f: db.delete(f); db.commit()
    return {"ok": True}

# ---------- FitPlay gate hook (placeholder) ----------
@app.get("/gate")
def gate(me: User = Depends(current_user)):
    return {"unlocked": True, "seconds": None}   # replace later with the real minute bank