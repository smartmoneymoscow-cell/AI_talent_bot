"""Подключение к БД и инициализация таблиц."""
import aiosqlite

from config import config

SCHEMA = """
-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY,
    telegram_id     INTEGER UNIQUE NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('employer','specialist')),
    full_name       TEXT NOT NULL,
    username        TEXT,
    bio             TEXT DEFAULT '',
    skills          TEXT DEFAULT '',          -- JSON array
    portfolio_url   TEXT DEFAULT '',
    hourly_rate     INTEGER DEFAULT 0,       -- ₽/час (для специалистов)
    budget_min      INTEGER DEFAULT 0,       -- бюджет от (для работодателей)
    budget_max      INTEGER DEFAULT 0,       -- бюджет до
    rating          REAL DEFAULT 0.0,
    rating_count    INTEGER DEFAULT 0,
    completed_jobs  INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    is_verified     INTEGER DEFAULT 0,       -- верифицирован (самозанятый)
    self_employed   INTEGER DEFAULT 0,       -- оформлен как самозанятый
    inn             TEXT DEFAULT '',          -- ИНН для самозанятости
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Заказы
CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY,
    employer_id     INTEGER NOT NULL REFERENCES users(id),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'ai_general',
    budget          INTEGER DEFAULT 0,
    deadline_days   INTEGER DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open','in_progress','review','completed','cancelled')),
    specialist_id   INTEGER REFERENCES users(id),
    payment_id      TEXT DEFAULT '',          -- ID платёжа в YooKassa
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Отклики
CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    specialist_id   INTEGER NOT NULL REFERENCES users(id),
    message         TEXT DEFAULT '',
    proposed_price  INTEGER DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','accepted','rejected','withdrawn')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, specialist_id)
);

-- Платежи
CREATE TABLE IF NOT EXISTS payments (
    id              INTEGER PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    payer_id        INTEGER NOT NULL REFERENCES users(id),
    receiver_id     INTEGER NOT NULL REFERENCES users(id),
    amount          INTEGER NOT NULL,         -- сумма в копейках
    platform_fee    INTEGER NOT NULL,
    yookassa_id     TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','waiting','succeeded','cancelled','refunded')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Рейтинг
CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    reviewer_id     INTEGER NOT NULL REFERENCES users(id),
    reviewee_id     INTEGER NOT NULL REFERENCES users(id),
    rating          INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment         TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, reviewer_id)
);
"""


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(config.DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()
