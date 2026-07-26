"""
Standalone server for Render deployment.
No package imports — everything self-contained.
"""
import hashlib
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
PLATFORM_FEE = float(os.getenv("PLATFORM_FEE_PERCENT", "5"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── DB ──────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('employer','specialist')),
    full_name TEXT NOT NULL, username TEXT, bio TEXT DEFAULT '',
    skills TEXT DEFAULT '', portfolio_url TEXT DEFAULT '',
    hourly_rate INTEGER DEFAULT 0, budget_min INTEGER DEFAULT 0,
    budget_max INTEGER DEFAULT 0, rating REAL DEFAULT 0.0,
    rating_count INTEGER DEFAULT 0, completed_jobs INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1, is_verified INTEGER DEFAULT 0,
    self_employed INTEGER DEFAULT 0, inn TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY, employer_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL, description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'ai_general', budget INTEGER DEFAULT 0,
    deadline_days INTEGER DEFAULT 0, status TEXT NOT NULL DEFAULT 'open'
    CHECK(status IN ('open','in_progress','review','completed','cancelled')),
    specialist_id INTEGER REFERENCES users(id), payment_id TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
    specialist_id INTEGER NOT NULL REFERENCES users(id),
    message TEXT DEFAULT '', proposed_price INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending','accepted','rejected','withdrawn')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, specialist_id)
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
    payer_id INTEGER NOT NULL REFERENCES users(id),
    receiver_id INTEGER NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL, platform_fee INTEGER NOT NULL,
    yookassa_id TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending','waiting','succeeded','cancelled','refunded')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
    reviewer_id INTEGER NOT NULL REFERENCES users(id),
    reviewee_id INTEGER NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, reviewer_id)
);
"""

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db

# ── Telegram validation ─────────────────────────────────────────
def validate_init_data(init_data: str) -> dict | None:
    try:
        parsed = parse_qs(init_data)
        if "hash" not in parsed: return None
        hash_from_tg = parsed["hash"][0]
        parts = [f"{k}={v[0]}" for k, v in sorted(parsed.items()) if k != "hash"]
        data_check = "\n".join(parts)
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if computed != hash_from_tg: return None
        auth_date = int(parsed.get("auth_date", ["0"])[0])
        if time.time() - auth_date > 86400: return None
        return json.loads(parsed.get("user", ["{}"])[0])
    except: return None

async def get_current_user(x_telegram_init_data: str = Header(alias="X-Telegram-Init-Data")):
    user_data = validate_init_data(x_telegram_init_data)
    if not user_data: raise HTTPException(401, "Invalid initData")
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (user_data["id"],))
        row = await cur.fetchone()
        if not row: raise HTTPException(404, "Register in bot first")
        return dict(row)
    finally: await db.close()

# ── Models ──────────────────────────────────────────────────────
class UserUpdate(BaseModel):
    bio: Optional[str] = None; skills: Optional[str] = None
    portfolio_url: Optional[str] = None; hourly_rate: Optional[int] = None

class OrderCreate(BaseModel):
    title: str; description: str; budget: Optional[int] = 0

class ApplicationCreate(BaseModel):
    order_id: int; message: Optional[str] = ""; proposed_price: Optional[int] = 0

class ReviewCreate(BaseModel):
    order_id: int; rating: int; comment: Optional[str] = ""

# ── App ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app):
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = await get_db()
    await db.executescript(SCHEMA); await db.commit(); await db.close()
    logger.info("Mini App backend started")
    yield

app = FastAPI(title="AI Talent Hub", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Routes ──────────────────────────────────────────────────────
@app.get("/api/me")
async def get_me(user=Depends(get_current_user)): return user

@app.patch("/api/me")
async def update_me(data: UserUpdate, user=Depends(get_current_user)):
    db = await get_db()
    try:
        fields = {k: v for k, v in data.model_dump().items() if v is not None}
        if fields:
            sc = ", ".join(f"{k}=?" for k in fields)
            await db.execute(f"UPDATE users SET {sc} WHERE telegram_id=?",
                           list(fields.values()) + [user["telegram_id"]])
            await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (user["telegram_id"],))
        return dict(await cur.fetchone())
    finally: await db.close()

@app.get("/api/me/stats")
async def get_stats(user=Depends(get_current_user)):
    db = await get_db()
    try:
        if user["role"] == "employer":
            cur = await db.execute("SELECT status,COUNT(*) as cnt FROM orders WHERE employer_id=? GROUP BY status", (user["id"],))
            obs = {r["status"]: r["cnt"] for r in await cur.fetchall()}
            cur = await db.execute("SELECT COALESCE(SUM(amount),0) as t FROM payments WHERE payer_id=? AND status='succeeded'", (user["id"],))
            return {"orders_by_status": obs, "total_spent": (await cur.fetchone())["t"]}
        else:
            cur = await db.execute("SELECT COUNT(*) as t FROM applications WHERE specialist_id=?", (user["id"],))
            ta = (await cur.fetchone())["t"]
            cur = await db.execute("SELECT COUNT(*) as t FROM applications WHERE specialist_id=? AND status='accepted'", (user["id"],))
            ac = (await cur.fetchone())["t"]
            cur = await db.execute("SELECT COALESCE(SUM(amount-platform_fee),0) as t FROM payments WHERE receiver_id=? AND status='succeeded'", (user["id"],))
            te = (await cur.fetchone())["t"]
            return {"total_applications": ta, "accepted_applications": ac, "total_earned": te,
                    "completed_jobs": user["completed_jobs"], "rating": user["rating"], "rating_count": user["rating_count"]}
    finally: await db.close()

@app.get("/api/orders")
async def list_orders(user=Depends(get_current_user), status: str = None, search: str = None,
                     min_budget: int = None, max_budget: int = None, sort: str = "newest", page: int = 0):
    db = await get_db()
    try:
        conds = ["o.employer_id=?"] if user["role"] == "employer" else ["o.status='open'"]
        params = [user["id"]] if user["role"] == "employer" else []
        if status: conds.append("o.status=?"); params.append(status)
        if search: conds.append("(o.title LIKE ? OR o.description LIKE ?)"); params += [f"%{search}%"]*2
        if min_budget: conds.append("o.budget>=?"); params.append(min_budget)
        if max_budget: conds.append("o.budget<=?"); params.append(max_budget)
        w = " AND ".join(conds) or "1=1"
        ob = "o.created_at DESC" if sort == "newest" else "o.budget ASC"
        cur = await db.execute(f"""SELECT o.*,u.full_name as employer_name,u.username as employer_username,
            (SELECT COUNT(*) FROM applications WHERE order_id=o.id) as applications_count
            FROM orders o JOIN users u ON o.employer_id=u.id WHERE {w} ORDER BY {ob} LIMIT 20 OFFSET ?""",
            params + [page*20])
        return [dict(r) for r in await cur.fetchall()]
    finally: await db.close()

@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("""SELECT o.*,u.full_name as employer_name,u.username as employer_username,
            u.telegram_id as employer_tg_id FROM orders o JOIN users u ON o.employer_id=u.id WHERE o.id=?""", (order_id,))
        row = await cur.fetchone()
        if not row: raise HTTPException(404)
        return dict(row)
    finally: await db.close()

@app.post("/api/orders")
async def create_order(data: OrderCreate, user=Depends(get_current_user)):
    if user["role"] != "employer": raise HTTPException(403)
    db = await get_db()
    try:
        cur = await db.execute("INSERT INTO orders(employer_id,title,description,budget) VALUES(?,?,?,?)",
                             (user["id"], data.title, data.description, data.budget or 0))
        await db.commit()
        cur = await db.execute("SELECT o.*,u.full_name as employer_name FROM orders o JOIN users u ON o.employer_id=u.id WHERE o.id=?",
                             (cur.lastrowid,))
        return dict(await cur.fetchone())
    finally: await db.close()

@app.get("/api/orders/{order_id}/applications")
async def get_apps(order_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("""SELECT a.*,u.full_name as specialist_name,u.username as specialist_username,
            u.rating as specialist_rating,u.completed_jobs as specialist_jobs,u.skills as specialist_skills,
            u.telegram_id as specialist_tg_id FROM applications a JOIN users u ON a.specialist_id=u.id
            WHERE a.order_id=? ORDER BY a.created_at DESC""", (order_id,))
        return [dict(r) for r in await cur.fetchall()]
    finally: await db.close()

@app.post("/api/applications")
async def create_app(data: ApplicationCreate, user=Depends(get_current_user)):
    if user["role"] != "specialist": raise HTTPException(403)
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM orders WHERE id=? AND status='open'", (data.order_id,))
        if not await cur.fetchone(): raise HTTPException(400, "Order not available")
        cur = await db.execute("SELECT 1 FROM applications WHERE order_id=? AND specialist_id=? AND status!='withdrawn'",
                             (data.order_id, user["id"]))
        if await cur.fetchone(): raise HTTPException(400, "Already applied")
        cur = await db.execute("INSERT INTO applications(order_id,specialist_id,message,proposed_price) VALUES(?,?,?,?)",
                             (data.order_id, user["id"], data.message or "", data.proposed_price or 0))
        await db.commit()
        return {"ok": True, "id": cur.lastrowid}
    finally: await db.close()

@app.patch("/api/applications/{app_id}/accept")
async def accept_app(app_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("SELECT a.*,o.employer_id,o.id as order_id FROM applications a JOIN orders o ON a.order_id=o.id WHERE a.id=?", (app_id,))
        r = await cur.fetchone()
        if not r or dict(r)["employer_id"] != user["id"]: raise HTTPException(403)
        a = dict(r)
        await db.execute("UPDATE applications SET status='accepted' WHERE id=?", (app_id,))
        await db.execute("UPDATE orders SET status='in_progress',specialist_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (a["specialist_id"], a["order_id"]))
        await db.execute("UPDATE applications SET status='rejected' WHERE order_id=? AND id!=?",
                        (a["order_id"], app_id))
        await db.commit()
        return {"ok": True}
    finally: await db.close()

@app.patch("/api/applications/{app_id}/reject")
async def reject_app(app_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("SELECT a.*,o.employer_id FROM applications a JOIN orders o ON a.order_id=o.id WHERE a.id=?", (app_id,))
        r = await cur.fetchone()
        if not r or dict(r)["employer_id"] != user["id"]: raise HTTPException(403)
        await db.execute("UPDATE applications SET status='rejected' WHERE id=?", (app_id,))
        await db.commit()
        return {"ok": True}
    finally: await db.close()

@app.patch("/api/orders/{order_id}/status")
async def update_status(order_id: int, status: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        o = await cur.fetchone()
        if not o or dict(o)["employer_id"] != user["id"]: raise HTTPException(403)
        await db.execute("UPDATE orders SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, order_id))
        await db.commit()
        return {"ok": True}
    finally: await db.close()

@app.get("/api/specialists")
async def list_specs(user=Depends(get_current_user), search: str = None, min_rating: float = None,
                    max_rate: int = None, page: int = 0):
    conds = ["role='specialist'", "is_active=1"]; params = []
    if search: conds.append("(full_name LIKE ? OR bio LIKE ? OR skills LIKE ?)"); params += [f"%{search}%"]*3
    if min_rating: conds.append("rating>=?"); params.append(min_rating)
    if max_rate: conds.append("hourly_rate<=? AND hourly_rate>0"); params.append(max_rate)
    w = " AND ".join(conds)
    db = await get_db()
    try:
        cur = await db.execute(f"""SELECT id,telegram_id,full_name,username,bio,skills,hourly_rate,
            rating,rating_count,completed_jobs,portfolio_url FROM users WHERE {w}
            ORDER BY rating DESC,completed_jobs DESC LIMIT 20 OFFSET ?""", params + [page*20])
        return [dict(r) for r in await cur.fetchall()]
    finally: await db.close()

@app.get("/api/specialists/{user_id}")
async def get_spec(user_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM users WHERE id=? AND role='specialist'", (user_id,))
        s = await cur.fetchone()
        if not s: raise HTTPException(404)
        cur = await db.execute("SELECT r.*,u.full_name as reviewer_name FROM reviews r JOIN users u ON r.reviewer_id=u.id WHERE r.reviewee_id=? ORDER BY r.created_at DESC LIMIT 10", (user_id,))
        return {**dict(s), "reviews": [dict(r) for r in await cur.fetchall()]}
    finally: await db.close()

@app.post("/api/reviews")
async def create_review(data: ReviewCreate, user=Depends(get_current_user)):
    if data.rating < 1 or data.rating > 5: raise HTTPException(400)
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM orders WHERE id=?", (data.order_id,))
        o = await cur.fetchone()
        if not o or dict(o)["status"] != "completed": raise HTTPException(400)
        o = dict(o)
        rid = o["specialist_id"] if user["role"] == "employer" else o["employer_id"]
        await db.execute("INSERT INTO reviews(order_id,reviewer_id,reviewee_id,rating,comment) VALUES(?,?,?,?,?)",
                        (data.order_id, user["id"], rid, data.rating, data.comment or ""))
        cur = await db.execute("SELECT AVG(rating) as a,COUNT(*) as c FROM reviews WHERE reviewee_id=?", (rid,))
        r = await cur.fetchone()
        await db.execute("UPDATE users SET rating=?,rating_count=? WHERE id=?",
                        (round(r["a"] or 0, 2), r["c"], rid))
        await db.commit()
        return {"ok": True}
    finally: await db.close()

@app.get("/api/avatar/{telegram_id}")
async def get_avatar(telegram_id: int):
    import aiohttp as aio
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos?user_id={telegram_id}&limit=1"
        async with aio.ClientSession() as s:
            async with s.get(url) as r:
                d = await r.json()
                if d.get("ok") and d["result"]["total_count"] > 0:
                    fid = d["result"]["photos"][0][-1]["file_id"]
                    async with s.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}") as r2:
                        fd = await r2.json()
                        if fd.get("ok"):
                            return {"url": f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fd['result']['file_path']}"}
        return {"url": None}
    except: return {"url": None}

# ── Static files ────────────────────────────────────────────────
DIST = os.path.join(os.path.dirname(__file__), "mini_app", "frontend", "dist")
if os.path.exists(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")
    @app.get("/{path:path}")
    async def serve(path: str):
        fp = os.path.join(DIST, path)
        if os.path.isfile(fp): return FileResponse(fp)
        return FileResponse(os.path.join(DIST, "index.html"))
