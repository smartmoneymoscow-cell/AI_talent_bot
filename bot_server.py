"""
Bot + health check for Render free tier.
Fully self-contained — no package imports needed.
"""
import asyncio
import logging
import os
import sys

import aiosqlite
from dotenv import load_dotenv

# Load env from script directory
_script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_script_dir, ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
MINI_APP_URL = os.getenv("MINI_APP_URL", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
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


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    await db.executescript(SCHEMA)
    await db.commit()
    await db.close()
    logger.info("DB initialized")


async def health_server():
    from aiohttp import web
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="🤖 Bot running"))
    app.router.add_get("/health", lambda r: web.Response(text="ok"))
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health server on port {port}")


async def run_bot():
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.fsm.storage.memory import MemoryStorage

    # Add parent dir to path so handlers can import from ai_talent_bot package
    parent = os.path.dirname(_script_dir)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    from ai_talent_bot.handlers import onboarding, profile, orders, applications, search, payments, voice

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(voice.router)
    dp.include_router(onboarding.router)
    dp.include_router(profile.router)
    dp.include_router(orders.router)
    dp.include_router(applications.router)
    dp.include_router(search.router)
    dp.include_router(payments.router)

    logger.info("Bot polling started!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def main():
    await init_db()
    await health_server()
    await run_bot()


if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        sys.exit(1)
    asyncio.run(main())
