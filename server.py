"""
Standalone server for Render deployment.
Serves FastAPI API + React Mini App static files.
No package imports — everything self-contained.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent / "data" / "bot.db"))
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
        if "hash" not in parsed:
            return None
        hash_from_tg = parsed["hash"][0]
        parts = [f"{k}={v[0]}" for k, v in sorted(parsed.items()) if k != "hash"]
        data_check = "\n".join(parts)
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if computed != hash_from_tg:
            return None
        auth_date = int(parsed.get("auth_date", ["0"])[0])
        if time.time() - auth_date > 86400:
            return None
        return json.loads(parsed.get("user", ["{}"])[0])
    except Exception:
        return None


async def get_current_user(x_telegram_init_data: str = Header(alias="X-Telegram-Init-Data")):
    user_data = validate_init_data(x_telegram_init_data)
    if not user_data:
        raise HTTPException(401, "Invalid initData")
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (user_data["id"],))
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Register in bot first")
        return dict(row)
    finally:
        await db.close()


# ── Models ──────────────────────────────────────────────────────
class UserUpdate(BaseModel):
    bio: Optional[str] = None
    skills: Optional[str] = None
    portfolio_url: Optional[str] = None
    hourly_rate: Optional[int] = None
    full_name: Optional[str] = None


class OrderCreate(BaseModel):
    title: str
    description: str
    category: Optional[str] = "ai_general"
    budget: Optional[int] = 0
    deadline_days: Optional[int] = 0


class ApplicationCreate(BaseModel):
    order_id: int
    message: Optional[str] = ""
    proposed_price: Optional[int] = 0


class ReviewCreate(BaseModel):
    order_id: int
    rating: int
    comment: Optional[str] = ""


class RegisterUser(BaseModel):
    role: str
    full_name: str
    bio: Optional[str] = ""
    skills: Optional[str] = ""
    portfolio_url: Optional[str] = ""
    hourly_rate: Optional[int] = 0


# ── Bot background task ─────────────────────────────────────────
_bot_task = None


async def _run_bot():
    """Start Telegram bot polling in background."""
    import sys as _sys
    _project_root = str(Path(__file__).resolve().parent)
    if _project_root not in _sys.path:
        _sys.path.insert(0, _project_root)

    try:
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.fsm.storage.memory import MemoryStorage
        from ai_talent_bot.config import config as bot_config
        from ai_talent_bot.database.db import init_db
        from ai_talent_bot.handlers import (
            onboarding, profile, orders, applications, search, payments, voice
        )
    except Exception as e:
        logger.error(f"Bot imports failed: {e}. Bot will NOT start.")
        return

    await init_db()
    logger.info("Bot DB initialized")

    try:
        from ai_talent_bot.utils.payments import init_yookassa
        init_yookassa()
    except Exception:
        pass

    bot = Bot(
        token=bot_config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(voice.router)
    dp.include_router(onboarding.router)
    dp.include_router(profile.router)
    dp.include_router(orders.router)
    dp.include_router(applications.router)
    dp.include_router(search.router)
    dp.include_router(payments.router)

    logger.info("Telegram bot polling started!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


# ── App ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app):
    global _bot_task

    # Init Mini App DB
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = await get_db()
    await db.executescript(SCHEMA)
    await db.commit()
    await db.close()
    logger.info("Mini App backend started")

    # Start Telegram bot in background
    if BOT_TOKEN:
        _bot_task = asyncio.create_task(_run_bot())
        _bot_task.add_done_callback(
            lambda t: logger.error(f"Bot task exited: {t.exception()}") if t.exception() else None
        )
    else:
        logger.warning("BOT_TOKEN not set — bot will NOT start")

    yield

    # Shutdown
    if _bot_task and not _bot_task.done():
        _bot_task.cancel()
        try:
            await _bot_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="AI Talent Hub", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Routes: Auth ────────────────────────────────────────────────
@app.get("/api/me")
async def get_me(user=Depends(get_current_user)):
    return user


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
    finally:
        await db.close()


@app.post("/api/switch-role")
async def switch_role(user=Depends(get_current_user)):
    """Switch role between employer and specialist."""
    new_role = "specialist" if user["role"] == "employer" else "employer"
    db = await get_db()
    try:
        await db.execute("UPDATE users SET role=? WHERE telegram_id=?",
                         (new_role, user["telegram_id"]))
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?",
                               (user["telegram_id"],))
        return dict(await cur.fetchone())
    finally:
        await db.close()


@app.post("/api/register")
async def register_user(data: RegisterUser, x_telegram_init_data: str = Header(alias="X-Telegram-Init-Data")):
    """Register a new user via Mini App."""
    if not x_telegram_init_data or not x_telegram_init_data.strip():
        raise HTTPException(400, "Откройте приложение через кнопку в боте")
    user_data = validate_init_data(x_telegram_init_data)
    if not user_data:
        raise HTTPException(400, "Данные Telegram невалидны. Откройте приложение через бота заново.")
    if data.role not in ("employer", "specialist"):
        raise HTTPException(400, "Invalid role")
    if len(data.full_name) < 2:
        raise HTTPException(400, "Name too short")

    db = await get_db()
    try:
        # Check if already registered
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (user_data["id"],))
        existing = await cur.fetchone()
        if existing:
            return dict(existing)

        await db.execute(
            """INSERT INTO users (telegram_id, role, full_name, username, bio, skills, portfolio_url, hourly_rate)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_data["id"], data.role, data.full_name,
             user_data.get("username", ""), data.bio or "",
             data.skills or "", data.portfolio_url or "", data.hourly_rate or 0)
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (user_data["id"],))
        return dict(await cur.fetchone())
    finally:
        await db.close()


# ── Routes: Stats ───────────────────────────────────────────────
@app.get("/api/me/stats")
async def get_stats(user=Depends(get_current_user)):
    db = await get_db()
    try:
        if user["role"] == "employer":
            cur = await db.execute(
                "SELECT status, COUNT(*) as cnt FROM orders WHERE employer_id=? GROUP BY status",
                (user["id"],))
            obs = {r["status"]: r["cnt"] for r in await cur.fetchall()}
            cur = await db.execute(
                "SELECT COALESCE(SUM(amount),0) as t FROM payments WHERE payer_id=? AND status='succeeded'",
                (user["id"],))
            return {"orders_by_status": obs, "total_spent": (await cur.fetchone())["t"]}
        else:
            cur = await db.execute(
                "SELECT COUNT(*) as t FROM applications WHERE specialist_id=?", (user["id"],))
            ta = (await cur.fetchone())["t"]
            cur = await db.execute(
                "SELECT COUNT(*) as t FROM applications WHERE specialist_id=? AND status='accepted'",
                (user["id"],))
            ac = (await cur.fetchone())["t"]
            cur = await db.execute(
                "SELECT COALESCE(SUM(amount-platform_fee),0) as t FROM payments WHERE receiver_id=? AND status='succeeded'",
                (user["id"],))
            te = (await cur.fetchone())["t"]
            return {
                "total_applications": ta, "accepted_applications": ac,
                "total_earned": te, "completed_jobs": user["completed_jobs"],
                "rating": user["rating"], "rating_count": user["rating_count"]
            }
    finally:
        await db.close()


# ── Routes: Orders ──────────────────────────────────────────────
@app.get("/api/orders")
async def list_orders(user=Depends(get_current_user), status: str = None, category: str = None,
                      search: str = None, min_budget: int = None, max_budget: int = None,
                      sort: str = "newest", page: int = 0, limit: int = 20):
    db = await get_db()
    try:
        conds = ["o.employer_id=?"] if user["role"] == "employer" else ["o.status='open'"]
        params = [user["id"]] if user["role"] == "employer" else []
        if status:
            conds.append("o.status=?")
            params.append(status)
        if category:
            conds.append("o.category=?")
            params.append(category)
        if search:
            conds.append("(o.title LIKE ? OR o.description LIKE ?)")
            params += [f"%{search}%"] * 2
        if min_budget:
            conds.append("o.budget>=?")
            params.append(min_budget)
        if max_budget:
            conds.append("o.budget<=?")
            params.append(max_budget)
        w = " AND ".join(conds) or "1=1"
        ob = "o.created_at DESC" if sort == "newest" else "o.budget ASC"
        offset = page * limit
        cur = await db.execute(f"""SELECT o.*,u.full_name as employer_name,u.username as employer_username,
            (SELECT COUNT(*) FROM applications WHERE order_id=o.id) as applications_count
            FROM orders o JOIN users u ON o.employer_id=u.id
            WHERE {w} ORDER BY {ob} LIMIT ? OFFSET ?""",
                               params + [limit, offset])
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("""SELECT o.*,u.full_name as employer_name,u.username as employer_username
            FROM orders o JOIN users u ON o.employer_id=u.id WHERE o.id=?""", (order_id,))
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Order not found")
        return dict(row)
    finally:
        await db.close()


@app.post("/api/orders")
async def create_order(data: OrderCreate, user=Depends(get_current_user)):
    if user["role"] != "employer":
        raise HTTPException(403, "Only employers can create orders")
    if len(data.title) < 5:
        raise HTTPException(400, "Title too short (min 5)")
    if len(data.description) < 20:
        raise HTTPException(400, "Description too short (min 20)")
    db = await get_db()
    try:
        cur = await db.execute(
            """INSERT INTO orders (employer_id,title,description,category,budget,deadline_days)
               VALUES (?,?,?,?,?,?)""",
            (user["id"], data.title, data.description,
             data.category or "ai_general", data.budget or 0, data.deadline_days or 0))
        await db.commit()
        cur2 = await db.execute("SELECT * FROM orders WHERE id=?", (cur.lastrowid,))
        return dict(await cur2.fetchone())
    finally:
        await db.close()


@app.patch("/api/orders/{order_id}/status")
async def update_order_status(order_id: int, status: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        order = await cur.fetchone()
        if not order:
            raise HTTPException(404, "Order not found")
        order = dict(order)
        if order["employer_id"] != user["id"]:
            raise HTTPException(403, "Not your order")
        valid = {"open": ["cancelled"], "in_progress": ["review", "cancelled"],
                 "review": ["completed", "cancelled"]}
        allowed = valid.get(order["status"], [])
        if status not in allowed:
            raise HTTPException(400, f"Cannot change {order['status']} → {status}")
        await db.execute("UPDATE orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (status, order_id))
        if status == "completed" and order.get("specialist_id"):
            await db.execute("UPDATE users SET completed_jobs=completed_jobs+1 WHERE id=?",
                             (order["specialist_id"],))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


# ── Routes: Applications ────────────────────────────────────────
@app.get("/api/orders/{order_id}/applications")
async def get_applications(order_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("""SELECT a.*,u.full_name as specialist_name,u.rating as specialist_rating,
            u.completed_jobs as specialist_jobs,u.skills as specialist_skills,
            u.telegram_id as specialist_tg_id
            FROM applications a JOIN users u ON a.specialist_id=u.id
            WHERE a.order_id=? ORDER BY a.created_at DESC""", (order_id,))
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@app.get("/api/my-applications")
async def my_applications(user=Depends(get_current_user), page: int = 0, limit: int = 20):
    """Get applications made by the current specialist."""
    if user["role"] != "specialist":
        raise HTTPException(403, "Only specialists")
    db = await get_db()
    try:
        offset = page * limit
        cur = await db.execute("""SELECT a.*,o.title as order_title,o.status as order_status,
            o.budget as order_budget,u.full_name as employer_name
            FROM applications a
            JOIN orders o ON a.order_id=o.id
            JOIN users u ON o.employer_id=u.id
            WHERE a.specialist_id=? ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
                               (user["id"], limit, offset))
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@app.post("/api/applications")
async def create_application(data: ApplicationCreate, user=Depends(get_current_user)):
    if user["role"] != "specialist":
        raise HTTPException(403, "Only specialists can apply")
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM orders WHERE id=?", (data.order_id,))
        order = await cur.fetchone()
        if not order or dict(order)["status"] != "open":
            raise HTTPException(400, "Order not available")
        cur = await db.execute("SELECT id FROM applications WHERE order_id=? AND specialist_id=?",
                               (data.order_id, user["id"]))
        if await cur.fetchone():
            raise HTTPException(409, "Already applied")
        await db.execute(
            "INSERT INTO applications (order_id,specialist_id,message,proposed_price) VALUES (?,?,?,?)",
            (data.order_id, user["id"], data.message or "", data.proposed_price or 0))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@app.patch("/api/applications/{app_id}/accept")
async def accept_application(app_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("""SELECT a.*,o.employer_id FROM applications a
            JOIN orders o ON a.order_id=o.id WHERE a.id=?""", (app_id,))
        app = await cur.fetchone()
        if not app:
            raise HTTPException(404, "Application not found")
        app = dict(app)
        if app["employer_id"] != user["id"]:
            raise HTTPException(403, "Not your order")
        await db.execute("UPDATE applications SET status='accepted' WHERE id=?", (app_id,))
        await db.execute("UPDATE orders SET status='in_progress',specialist_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (app["specialist_id"], app["order_id"]))
        # Reject others
        await db.execute("""UPDATE applications SET status='rejected'
            WHERE order_id=? AND id!=? AND status='pending'""",
                         (app["order_id"], app_id))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@app.patch("/api/applications/{app_id}/reject")
async def reject_application(app_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("""SELECT a.*,o.employer_id FROM applications a
            JOIN orders o ON a.order_id=o.id WHERE a.id=?""", (app_id,))
        app = await cur.fetchone()
        if not app:
            raise HTTPException(404, "Not found")
        if dict(app)["employer_id"] != user["id"]:
            raise HTTPException(403, "Not your order")
        await db.execute("UPDATE applications SET status='rejected' WHERE id=?", (app_id,))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


# ── Routes: Specialists search ──────────────────────────────────
@app.get("/api/specialists")
async def list_specialists(user=Depends(get_current_user), search: str = None,
                           max_rate: int = None, sort: str = "rating", page: int = 0, limit: int = 20):
    db = await get_db()
    try:
        conds = ["role='specialist'", "is_active=1"]
        params = []
        if search:
            conds.append("(skills LIKE ? OR full_name LIKE ?)")
            params += [f"%{search}%"] * 2
        if max_rate:
            conds.append("hourly_rate<=?")
            params.append(max_rate)
        w = " AND ".join(conds)
        ob = "rating DESC, completed_jobs DESC" if sort == "rating" else "hourly_rate ASC"
        offset = page * limit
        cur = await db.execute(f"""SELECT id,telegram_id,full_name,username,bio,skills,
            portfolio_url,hourly_rate,rating,rating_count,completed_jobs
            FROM users WHERE {w} ORDER BY {ob} LIMIT ? OFFSET ?""",
                               params + [limit, offset])
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@app.get("/api/specialists/{spec_id}")
async def get_specialist(spec_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cur = await db.execute("""SELECT id,telegram_id,full_name,username,bio,skills,
            portfolio_url,hourly_rate,rating,rating_count,completed_jobs
            FROM users WHERE id=? AND role='specialist'""", (spec_id,))
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        return dict(row)
    finally:
        await db.close()


# ── Routes: Reviews ─────────────────────────────────────────────
@app.get("/api/reviews")
async def get_reviews(user=Depends(get_current_user), page: int = 0, limit: int = 20):
    db = await get_db()
    try:
        offset = page * limit
        cur = await db.execute("""SELECT r.*,u.full_name as reviewer_name,o.title as order_title
            FROM reviews r JOIN users u ON r.reviewer_id=u.id JOIN orders o ON r.order_id=o.id
            WHERE r.reviewee_id=? ORDER BY r.created_at DESC LIMIT ? OFFSET ?""",
                               (user["id"], limit, offset))
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@app.post("/api/reviews")
async def create_review(data: ReviewCreate, user=Depends(get_current_user)):
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(400, "Rating must be 1-5")
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM orders WHERE id=?", (data.order_id,))
        order = await cur.fetchone()
        if not order:
            raise HTTPException(404, "Order not found")
        order = dict(order)
        if order["status"] != "completed":
            raise HTTPException(400, "Order not completed")
        # Determine reviewee
        if user["id"] == order["employer_id"]:
            reviewee_id = order["specialist_id"]
        elif user["id"] == order.get("specialist_id"):
            reviewee_id = order["employer_id"]
        else:
            raise HTTPException(403, "Not involved in this order")
        if not reviewee_id:
            raise HTTPException(400, "No specialist assigned")
        # Check duplicate
        cur = await db.execute("SELECT id FROM reviews WHERE order_id=? AND reviewer_id=?",
                               (data.order_id, user["id"]))
        if await cur.fetchone():
            raise HTTPException(409, "Already reviewed")
        await db.execute("INSERT INTO reviews (order_id,reviewer_id,reviewee_id,rating,comment) VALUES (?,?,?,?,?)",
                         (data.order_id, user["id"], reviewee_id, data.rating, data.comment or ""))
        # Update rating
        cur = await db.execute("SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM reviews WHERE reviewee_id=?",
                               (reviewee_id,))
        stats = await cur.fetchone()
        await db.execute("UPDATE users SET rating=?, rating_count=? WHERE id=?",
                         (round(stats["avg_r"], 1), stats["cnt"], reviewee_id))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


# ── Routes: Avatar ──────────────────────────────────────────────
@app.get("/api/avatar/{tg_id}")
async def get_avatar(tg_id: int):
    """Proxy Telegram user avatar."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Get user profile photos
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos?user_id={tg_id}&limit=1"
            async with session.get(url) as resp:
                data = await resp.json()
                if not data.get("ok") or not data["result"]["total_count"]:
                    return JSONResponse({"url": None})
                file_id = data["result"]["photos"][0][-1]["file_id"]
                # Get file path
                url2 = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                async with session.get(url2) as resp2:
                    data2 = await resp2.json()
                    if data2.get("ok"):
                        file_path = data2["result"]["file_path"]
                        return JSONResponse({"url": f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"})
        return JSONResponse({"url": None})
    except Exception:
        return JSONResponse({"url": None})


# ── Health / Keep-alive ─────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "bot": "running" if _bot_task and not _bot_task.done() else "stopped"}


# ── Catch-all: serve React SPA ─────────────────────────────────-
FRONTEND_DIR = Path(__file__).resolve().parent / "mini_app" / "frontend" / "dist"

# Mount static assets (JS, CSS, images) BEFORE the catch-all
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="static-assets")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve React SPA for all non-API routes."""
    # Try to serve exact file first (favicon, manifest, etc.)
    file_path = FRONTEND_DIR / full_path
    if full_path and file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    # Serve index.html for SPA routing
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"error": "Frontend not built. Run: cd mini_app/frontend && npm run build"}, status_code=500)
