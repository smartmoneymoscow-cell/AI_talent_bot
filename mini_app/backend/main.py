"""
Telegram Mini App — FastAPI Backend
Переиспользует БД от aiogram-бота.
"""
import hashlib
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, unquote

from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_talent_bot.database.db import get_db, init_db
from ai_talent_bot.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Telegram initData валидация ────────────────────────────────

def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """Проверка подписи Telegram WebApp initData."""
    try:
        parsed = parse_qs(init_data)
        if "hash" not in parsed:
            return None

        hash_from_tg = parsed["hash"][0]
        data_check_string_parts = []

        for key, values in sorted(parsed.items()):
            if key == "hash":
                continue
            data_check_string_parts.append(f"{key}={values[0]}")

        data_check_string = "\n".join(data_check_string_parts)

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256,
        ).digest()

        computed_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if computed_hash != hash_from_tg:
            return None

        # Проверяем时效 (макс 24 часа)
        auth_date = int(parsed.get("auth_date", ["0"])[0])
        if time.time() - auth_date > 86400:
            return None

        user_data = json.loads(parsed.get("user", ["{}"])[0])
        return user_data
    except Exception as e:
        logger.error("InitData validation error: %s", e)
        return None


# ── Dependency: текущий пользователь ───────────────────────────

async def get_current_user(x_telegram_init_data: str = Header(alias="X-Telegram-Init-Data")):
    user_data = validate_init_data(x_telegram_init_data, config.BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram initData")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (user_data["id"],),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found. Register in bot first.")
        return dict(row)
    finally:
        await db.close()


# ── Lifespan ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Mini App backend started")
    yield


# ── FastAPI App ────────────────────────────────────────────────

app = FastAPI(title="AI Talent Hub — Mini App API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ────────────────────────────────────────────

class UserUpdate(BaseModel):
    bio: Optional[str] = None
    skills: Optional[str] = None
    portfolio_url: Optional[str] = None
    hourly_rate: Optional[int] = None

class OrderCreate(BaseModel):
    title: str
    description: str
    budget: Optional[int] = 0

class ApplicationCreate(BaseModel):
    order_id: int
    message: Optional[str] = ""
    proposed_price: Optional[int] = 0

class ReviewCreate(BaseModel):
    order_id: int
    rating: int
    comment: Optional[str] = ""


# ── AUTH ───────────────────────────────────────────────────────

@app.get("/api/me")
async def get_me(user=Depends(get_current_user)):
    return user


@app.patch("/api/me")
async def update_me(data: UserUpdate, user=Depends(get_current_user)):
    db = await get_db()
    try:
        fields = {}
        if data.bio is not None:
            fields["bio"] = data.bio
        if data.skills is not None:
            fields["skills"] = data.skills
        if data.portfolio_url is not None:
            fields["portfolio_url"] = data.portfolio_url
        if data.hourly_rate is not None:
            fields["hourly_rate"] = data.hourly_rate

        if fields:
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            await db.execute(
                f"UPDATE users SET {set_clause} WHERE telegram_id = ?",
                list(fields.values()) + [user["telegram_id"]],
            )
            await db.commit()

        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (user["telegram_id"],))
        return dict(await cursor.fetchone())
    finally:
        await db.close()


@app.get("/api/me/stats")
async def get_my_stats(user=Depends(get_current_user)):
    db = await get_db()
    try:
        if user["role"] == "employer":
            cursor = await db.execute(
                "SELECT status, COUNT(*) as cnt FROM orders WHERE employer_id = ? GROUP BY status",
                (user["id"],),
            )
            rows = await cursor.fetchall()
            orders_by_status = {r["status"]: r["cnt"] for r in rows}

            cursor = await db.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE payer_id = ? AND status = 'succeeded'",
                (user["id"],),
            )
            total_spent = (await cursor.fetchone())["total"]

            return {"orders_by_status": orders_by_status, "total_spent": total_spent}
        else:
            cursor = await db.execute(
                "SELECT COUNT(*) as total FROM applications WHERE specialist_id = ?", (user["id"],)
            )
            total_apps = (await cursor.fetchone())["total"]

            cursor = await db.execute(
                "SELECT COUNT(*) as total FROM applications WHERE specialist_id = ? AND status = 'accepted'",
                (user["id"],),
            )
            accepted = (await cursor.fetchone())["total"]

            cursor = await db.execute(
                "SELECT COALESCE(SUM(amount - platform_fee), 0) as total FROM payments WHERE receiver_id = ? AND status = 'succeeded'",
                (user["id"],),
            )
            total_earned = (await cursor.fetchone())["total"]

            return {
                "total_applications": total_apps,
                "accepted_applications": accepted,
                "total_earned": total_earned,
                "completed_jobs": user["completed_jobs"],
                "rating": user["rating"],
                "rating_count": user["rating_count"],
            }
    finally:
        await db.close()


# ── ORDERS ─────────────────────────────────────────────────────

@app.get("/api/orders")
async def list_orders(
    user=Depends(get_current_user),
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_budget: Optional[int] = None,
    max_budget: Optional[int] = None,
    sort: Optional[str] = "newest",
    page: int = 0,
    limit: int = 20,
):
    db = await get_db()
    try:
        if user["role"] == "employer":
            conditions = ["o.employer_id = ?"]
            params = [user["id"]]
        else:
            conditions = ["o.status = 'open'"]
            params = []

        if status:
            conditions.append("o.status = ?")
            params.append(status)
        if category:
            conditions.append("o.category = ?")
            params.append(category)
        if search:
            conditions.append("(o.title LIKE ? OR o.description LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])
        if min_budget is not None:
            conditions.append("o.budget >= ?")
            params.append(min_budget)
        if max_budget is not None:
            conditions.append("o.budget <= ?")
            params.append(max_budget)

        where = " AND ".join(conditions) if conditions else "1=1"
        order_by = "o.created_at DESC" if sort == "newest" else "o.budget ASC"

        offset = page * limit

        cursor = await db.execute(
            f"""SELECT o.*, u.full_name as employer_name, u.username as employer_username,
                       (SELECT COUNT(*) FROM applications WHERE order_id = o.id) as applications_count
                FROM orders o JOIN users u ON o.employer_id = u.id
                WHERE {where}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT o.*, u.full_name as employer_name, u.username as employer_username,
                      u.telegram_id as employer_tg_id
               FROM orders o JOIN users u ON o.employer_id = u.id
               WHERE o.id = ?""",
            (order_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return dict(row)
    finally:
        await db.close()


@app.post("/api/orders")
async def create_order(data: OrderCreate, user=Depends(get_current_user)):
    if user["role"] != "employer":
        raise HTTPException(status_code=403, detail="Only employers can create orders")

    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO orders (employer_id, title, description, budget) VALUES (?, ?, ?, ?)",
            (user["id"], data.title, data.description, data.budget or 0),
        )
        await db.commit()
        order_id = cursor.lastrowid
        cursor = await db.execute(
            """SELECT o.*, u.full_name as employer_name FROM orders o
               JOIN users u ON o.employer_id = u.id WHERE o.id = ?""",
            (order_id,),
        )
        return dict(await cursor.fetchone())
    finally:
        await db.close()


@app.patch("/api/orders/{order_id}/status")
async def update_order_status(order_id: int, status: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = await cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order = dict(order)

        if order["employer_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not your order")

        await db.execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, order_id),
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


# ── APPLICATIONS ───────────────────────────────────────────────

@app.get("/api/orders/{order_id}/applications")
async def get_applications(order_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.*, u.full_name as specialist_name, u.username as specialist_username,
                      u.rating as specialist_rating, u.completed_jobs as specialist_jobs,
                      u.skills as specialist_skills, u.telegram_id as specialist_tg_id
               FROM applications a JOIN users u ON a.specialist_id = u.id
               WHERE a.order_id = ?
               ORDER BY a.created_at DESC""",
            (order_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@app.post("/api/applications")
async def create_application(data: ApplicationCreate, user=Depends(get_current_user)):
    if user["role"] != "specialist":
        raise HTTPException(status_code=403, detail="Only specialists can apply")

    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (data.order_id,))
        order = await cursor.fetchone()
        if not order or dict(order)["status"] != "open":
            raise HTTPException(status_code=400, detail="Order not available")

        # Проверяем, не откликался ли уже
        cursor = await db.execute(
            "SELECT 1 FROM applications WHERE order_id = ? AND specialist_id = ? AND status != 'withdrawn'",
            (data.order_id, user["id"]),
        )
        if await cursor.fetchone():
            raise HTTPException(status_code=400, detail="Already applied")

        cursor = await db.execute(
            "INSERT INTO applications (order_id, specialist_id, message, proposed_price) VALUES (?, ?, ?, ?)",
            (data.order_id, user["id"], data.message or "", data.proposed_price or 0),
        )
        await db.commit()
        return {"ok": True, "id": cursor.lastrowid}
    finally:
        await db.close()


@app.patch("/api/applications/{app_id}/accept")
async def accept_application(app_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.*, o.employer_id, o.id as order_id FROM applications a
               JOIN orders o ON a.order_id = o.id WHERE a.id = ?""",
            (app_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Application not found")
        app = dict(row)

        if app["employer_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not your order")

        # Принимаем
        await db.execute("UPDATE applications SET status = 'accepted' WHERE id = ?", (app_id,))
        await db.execute(
            "UPDATE orders SET status = 'in_progress', specialist_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (app["specialist_id"], app["order_id"]),
        )
        # Отклоняем остальные
        await db.execute(
            "UPDATE applications SET status = 'rejected' WHERE order_id = ? AND id != ?",
            (app["order_id"], app_id),
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@app.patch("/api/applications/{app_id}/reject")
async def reject_application(app_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.*, o.employer_id FROM applications a
               JOIN orders o ON a.order_id = o.id WHERE a.id = ?""",
            (app_id,),
        )
        row = await cursor.fetchone()
        if not row or dict(row)["employer_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")

        await db.execute("UPDATE applications SET status = 'rejected' WHERE id = ?", (app_id,))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


# ── SPECIALISTS ────────────────────────────────────────────────

@app.get("/api/specialists")
async def list_specialists(
    user=Depends(get_current_user),
    search: Optional[str] = None,
    min_rating: Optional[float] = None,
    max_rate: Optional[int] = None,
    skills: Optional[str] = None,
    page: int = 0,
    limit: int = 20,
):
    conditions = ["role = 'specialist'", "is_active = 1"]
    params = []

    if search:
        conditions.append("(full_name LIKE ? OR bio LIKE ? OR skills LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if min_rating is not None:
        conditions.append("rating >= ?")
        params.append(min_rating)
    if max_rate is not None:
        conditions.append("hourly_rate <= ? AND hourly_rate > 0")
        params.append(max_rate)
    if skills:
        conditions.append("skills LIKE ?")
        params.append(f"%{skills}%")

    where = " AND ".join(conditions)
    offset = page * limit

    db = await get_db()
    try:
        cursor = await db.execute(
            f"""SELECT id, telegram_id, full_name, username, bio, skills,
                       hourly_rate, rating, rating_count, completed_jobs,
                       portfolio_url, self_employed
                FROM users WHERE {where}
                ORDER BY rating DESC, completed_jobs DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@app.get("/api/specialists/{user_id}")
async def get_specialist(user_id: int, user=Depends(get_current_user)):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ? AND role = 'specialist'",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Specialist not found")
        spec = dict(row)

        # Отзывы
        cursor = await db.execute(
            """SELECT r.*, u.full_name as reviewer_name
               FROM reviews r JOIN users u ON r.reviewer_id = u.id
               WHERE r.reviewee_id = ? ORDER BY r.created_at DESC LIMIT 10""",
            (user_id,),
        )
        reviews = [dict(r) for r in await cursor.fetchall()]

        return {**spec, "reviews": reviews}
    finally:
        await db.close()


# ── REVIEWS ────────────────────────────────────────────────────

@app.post("/api/reviews")
async def create_review(data: ReviewCreate, user=Depends(get_current_user)):
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (data.order_id,))
        order = await cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order = dict(order)

        if order["status"] != "completed":
            raise HTTPException(status_code=400, detail="Order not completed yet")

        if user["role"] == "employer":
            reviewee_id = order["specialist_id"]
        else:
            reviewee_id = order["employer_id"]

        cursor = await db.execute(
            "INSERT INTO reviews (order_id, reviewer_id, reviewee_id, rating, comment) VALUES (?, ?, ?, ?, ?)",
            (data.order_id, user["id"], reviewee_id, data.rating, data.comment or ""),
        )
        await db.commit()

        # Обновляем рейтинг
        cursor = await db.execute(
            "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM reviews WHERE reviewee_id = ?",
            (reviewee_id,),
        )
        row = await cursor.fetchone()
        avg_r = round(row["avg_r"], 2) if row["avg_r"] else 0
        cnt = row["cnt"]
        await db.execute("UPDATE users SET rating = ?, rating_count = ? WHERE id = ?", (avg_r, cnt, reviewee_id))
        await db.commit()

        return {"ok": True}
    finally:
        await db.close()


# ── TG AVATAR PROXY ────────────────────────────────────────────

@app.get("/api/avatar/{telegram_id}")
async def get_avatar(telegram_id: int):
    """Прокси для аватарки из Telegram."""
    import aiohttp as aiohttp_lib
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getUserProfilePhotos?user_id={telegram_id}&limit=1"
        async with aiohttp_lib.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get("ok") and data["result"]["total_count"] > 0:
                    file_id = data["result"]["photos"][0][-1]["file_id"]
                    file_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getFile?file_id={file_id}"
                    async with session.get(file_url) as resp2:
                        file_data = await resp2.json()
                        if file_data.get("ok"):
                            photo_path = file_data["result"]["file_path"]
                            return {"url": f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{photo_path}"}
        return {"url": None}
    except Exception:
        return {"url": None}


# ── STATIC FILES ───────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
