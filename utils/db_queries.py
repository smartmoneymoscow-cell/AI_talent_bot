"""Модуль работы с БД — все SQL-запросы в одном месте."""
from __future__ import annotations

import json
from typing import Any

from ai_talent_bot.database.db import get_db


# ── Пользователи ──────────────────────────────────────────────

async def create_user(telegram_id: int, role: str, full_name: str, username: str = "") -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO users (telegram_id, role, full_name, username) VALUES (?, ?, ?, ?)",
            (telegram_id, role, full_name, username),
        )
        await db.commit()
        return await get_user_by_tg(telegram_id)
    finally:
        await db.close()


async def get_user_by_tg(telegram_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_user_by_id(user_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def update_user(telegram_id: int, **fields: Any) -> dict | None:
    if not fields:
        return await get_user_by_tg(telegram_id)
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [telegram_id]
    db = await get_db()
    try:
        await db.execute(f"UPDATE users SET {set_clause} WHERE telegram_id = ?", values)
        await db.commit()
        return await get_user_by_tg(telegram_id)
    finally:
        await db.close()


async def search_specialists(
    query: str = "",
    category: str = "",
    min_rating: float = 0,
    max_rate: int = 0,
    page: int = 0,
    per_page: int = 5,
) -> tuple[list[dict], bool]:
    """Поиск специалистов с фильтрацией."""
    conditions = ["role = 'specialist'", "is_active = 1"]
    params: list[Any] = []

    if query:
        conditions.append("(full_name LIKE ? OR bio LIKE ? OR skills LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like, like])
    if category:
        conditions.append("skills LIKE ?")
        params.append(f"%{category}%")
    if min_rating:
        conditions.append("rating >= ?")
        params.append(min_rating)
    if max_rate:
        conditions.append("hourly_rate <= ? AND hourly_rate > 0")
        params.append(max_rate)

    where = " AND ".join(conditions)
    offset = page * per_page

    db = await get_db()
    try:
        count_q = f"SELECT COUNT(*) as cnt FROM users WHERE {where}"
        cursor = await db.execute(count_q, params)
        total = (await cursor.fetchone())["cnt"]

        q = f"SELECT * FROM users WHERE {where} ORDER BY rating DESC, completed_jobs DESC LIMIT ? OFFSET ?"
        cursor = await db.execute(q, params + [per_page + 1, offset])
        rows = await cursor.fetchall()
        items = [dict(r) for r in rows[:per_page]]
        has_next = len(rows) > per_page
        return items, has_next
    finally:
        await db.close()


# ── Заказы ────────────────────────────────────────────────────

async def create_order(
    employer_id: int,
    title: str,
    description: str,
    category: str = "ai_general",
    budget: int = 0,
    deadline_days: int = 0,
) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO orders (employer_id, title, description, category, budget, deadline_days)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (employer_id, title, description, category, budget, deadline_days),
        )
        await db.commit()
        order_id = cursor.lastrowid
        return await get_order_by_id(order_id)
    finally:
        await db.close()


async def get_order_by_id(order_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT o.*, u.full_name as employer_name, u.telegram_id as employer_tg_id
               FROM orders o JOIN users u ON o.employer_id = u.id
               WHERE o.id = ?""",
            (order_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_orders_by_employer(employer_tg_id: int, page: int = 0, per_page: int = 5) -> tuple[list[dict], bool]:
    db = await get_db()
    try:
        offset = page * per_page
        cursor = await db.execute(
            """SELECT o.*, u.full_name as employer_name
               FROM orders o JOIN users u ON o.employer_id = u.id
               WHERE o.employer_id = (SELECT id FROM users WHERE telegram_id = ?)
               ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
            (employer_tg_id, per_page + 1, offset),
        )
        rows = await cursor.fetchall()
        items = [dict(r) for r in rows[:per_page]]
        has_next = len(rows) > per_page
        return items, has_next
    finally:
        await db.close()


async def get_open_orders(
    category: str = "",
    page: int = 0,
    per_page: int = 5,
) -> tuple[list[dict], bool]:
    db = await get_db()
    try:
        conditions = ["o.status = 'open'"]
        params: list[Any] = []
        if category:
            conditions.append("o.category = ?")
            params.append(category)
        where = " AND ".join(conditions)
        offset = page * per_page

        count_q = f"SELECT COUNT(*) as cnt FROM orders o WHERE {where}"
        cursor = await db.execute(count_q, params)
        total = (await cursor.fetchone())["cnt"]

        q = f"""SELECT o.*, u.full_name as employer_name
                FROM orders o JOIN users u ON o.employer_id = u.id
                WHERE {where}
                ORDER BY o.created_at DESC LIMIT ? OFFSET ?"""
        cursor = await db.execute(q, params + [per_page + 1, offset])
        rows = await cursor.fetchall()
        items = [dict(r) for r in rows[:per_page]]
        has_next = len(rows) > per_page
        return items, has_next
    finally:
        await db.close()


async def update_order_status(order_id: int, status: str, specialist_id: int | None = None) -> dict | None:
    db = await get_db()
    try:
        if specialist_id:
            await db.execute(
                "UPDATE orders SET status = ?, specialist_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, specialist_id, order_id),
            )
        else:
            await db.execute(
                "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, order_id),
            )
        await db.commit()
        return await get_order_by_id(order_id)
    finally:
        await db.close()


async def get_orders_by_specialist(specialist_tg_id: int, page: int = 0, per_page: int = 5) -> tuple[list[dict], bool]:
    db = await get_db()
    try:
        offset = page * per_page
        cursor = await db.execute(
            """SELECT o.*, u.full_name as employer_name
               FROM orders o JOIN users u ON o.employer_id = u.id
               WHERE o.specialist_id = (SELECT id FROM users WHERE telegram_id = ?)
               ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
            (specialist_tg_id, per_page + 1, offset),
        )
        rows = await cursor.fetchall()
        items = [dict(r) for r in rows[:per_page]]
        has_next = len(rows) > per_page
        return items, has_next
    finally:
        await db.close()


# ── Отклики ───────────────────────────────────────────────────

async def create_application(order_id: int, specialist_id: int, message: str, proposed_price: int) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO applications (order_id, specialist_id, message, proposed_price) VALUES (?, ?, ?, ?)",
            (order_id, specialist_id, message, proposed_price),
        )
        await db.commit()
        app_id = cursor.lastrowid
        return await get_application_by_id(app_id)
    finally:
        await db.close()


async def get_application_by_id(app_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.*, u.full_name as specialist_name, u.rating as specialist_rating,
                      u.telegram_id as specialist_tg_id
               FROM applications a JOIN users u ON a.specialist_id = u.id
               WHERE a.id = ?""",
            (app_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_applications_for_order(order_id: int) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.*, u.full_name as specialist_name, u.rating as specialist_rating,
                      u.completed_jobs as specialist_jobs, u.telegram_id as specialist_tg_id
               FROM applications a JOIN users u ON a.specialist_id = u.id
               WHERE a.order_id = ? ORDER BY a.created_at DESC""",
            (order_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_applications_by_specialist(specialist_tg_id: int, page: int = 0, per_page: int = 5) -> tuple[list[dict], bool]:
    db = await get_db()
    try:
        offset = page * per_page
        cursor = await db.execute(
            """SELECT a.*, o.title as order_title, o.status as order_status, o.budget as order_budget
               FROM applications a
               JOIN orders o ON a.order_id = o.id
               WHERE a.specialist_id = (SELECT id FROM users WHERE telegram_id = ?)
               ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
            (specialist_tg_id, per_page + 1, offset),
        )
        rows = await cursor.fetchall()
        items = [dict(r) for r in rows[:per_page]]
        has_next = len(rows) > per_page
        return items, has_next
    finally:
        await db.close()


async def update_application_status(app_id: int, status: str) -> dict | None:
    db = await get_db()
    try:
        await db.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
        await db.commit()
        return await get_application_by_id(app_id)
    finally:
        await db.close()


async def has_applied(order_id: int, specialist_id: int) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT 1 FROM applications WHERE order_id = ? AND specialist_id = ? AND status != 'withdrawn'",
            (order_id, specialist_id),
        )
        return await cursor.fetchone() is not None
    finally:
        await db.close()


# ── Рейтинг ──────────────────────────────────────────────────

async def add_review(order_id: int, reviewer_id: int, reviewee_id: int, rating: int, comment: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO reviews (order_id, reviewer_id, reviewee_id, rating, comment) VALUES (?, ?, ?, ?, ?)",
            (order_id, reviewer_id, reviewee_id, rating, comment),
        )
        await db.commit()

        # Обновляем средний рейтинг
        cursor = await db.execute(
            "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM reviews WHERE reviewee_id = ?",
            (reviewee_id,),
        )
        row = await cursor.fetchone()
        avg_r = round(row["avg_r"], 2) if row["avg_r"] else 0
        cnt = row["cnt"]

        await db.execute(
            "UPDATE users SET rating = ?, rating_count = ? WHERE id = ?",
            (avg_r, cnt, reviewee_id),
        )
        await db.commit()
        return {"rating": rating, "comment": comment}
    finally:
        await db.close()


async def get_reviews_for_user(user_id: int, page: int = 0, per_page: int = 5) -> tuple[list[dict], bool]:
    db = await get_db()
    try:
        offset = page * per_page
        cursor = await db.execute(
            """SELECT r.*, u.full_name as reviewer_name, o.title as order_title
               FROM reviews r
               JOIN users u ON r.reviewer_id = u.id
               JOIN orders o ON r.order_id = o.id
               WHERE r.reviewee_id = ?
               ORDER BY r.created_at DESC LIMIT ? OFFSET ?""",
            (user_id, per_page + 1, offset),
        )
        rows = await cursor.fetchall()
        items = [dict(r) for r in rows[:per_page]]
        has_next = len(rows) > per_page
        return items, has_next
    finally:
        await db.close()


# ── Платежи ──────────────────────────────────────────────────

async def create_payment(order_id: int, payer_id: int, receiver_id: int, amount: int, platform_fee: int) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO payments (order_id, payer_id, receiver_id, amount, platform_fee) VALUES (?, ?, ?, ?, ?)",
            (order_id, payer_id, receiver_id, amount, platform_fee),
        )
        await db.commit()
        payment_id = cursor.lastrowid
        cursor = await db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        return dict(await cursor.fetchone())
    finally:
        await db.close()


async def update_payment(payment_id: int, **fields: Any) -> dict | None:
    if not fields:
        return None
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [payment_id]
    db = await get_db()
    try:
        await db.execute(f"UPDATE payments SET {set_clause} WHERE id = ?", values)
        await db.commit()
        cursor = await db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_payment_by_order(order_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def increment_completed(user_id: int):
    db = await get_db()
    try:
        await db.execute("UPDATE users SET completed_jobs = completed_jobs + 1 WHERE id = ?", (user_id,))
        await db.commit()
    finally:
        await db.close()


# ── Статистика ────────────────────────────────────────────────

async def get_user_stats(telegram_id: int) -> dict:
    db = await get_db()
    try:
        user = await (await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))).fetchone()
        if not user:
            return {}
        user = dict(user)
        if user["role"] == "employer":
            orders = await (await db.execute(
                "SELECT status, COUNT(*) as cnt FROM orders WHERE employer_id = ? GROUP BY status",
                (user["id"],),
            )).fetchall()
            total_spent = await (await db.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE payer_id = ? AND status = 'succeeded'",
                (user["id"],),
            )).fetchone()
            return {
                "user": user,
                "orders_by_status": {r["status"]: r["cnt"] for r in orders},
                "total_spent": total_spent["total"],
            }
        else:
            apps = await (await db.execute(
                "SELECT COUNT(*) as total FROM applications WHERE specialist_id = ?",
                (user["id"],),
            )).fetchone()
            accepted = await (await db.execute(
                "SELECT COUNT(*) as total FROM applications WHERE specialist_id = ? AND status = 'accepted'",
                (user["id"],),
            )).fetchone()
            total_earned = await (await db.execute(
                "SELECT COALESCE(SUM(amount - platform_fee), 0) as total FROM payments WHERE receiver_id = ? AND status = 'succeeded'",
                (user["id"],),
            )).fetchone()
            return {
                "user": user,
                "total_applications": apps["total"],
                "accepted_applications": accepted["total"],
                "total_earned": total_earned["total"],
            }
    finally:
        await db.close()
