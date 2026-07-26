"""Точка входа бота."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from ai_talent_bot.config import config
from ai_talent_bot.database.db import init_db
from ai_talent_bot.handlers import onboarding, profile, orders, applications, search, payments, voice


async def on_startup(bot: Bot):
    """Действия при запуске."""
    logging.info("Инициализация базы данных...")
    await init_db()
    logging.info("Инициализация YooKassa...")
    from ai_talent_bot.utils.payments import init_yookassa
    if init_yookassa():
        logging.info("YooKassa: OK")
    else:
        logging.warning("YooKassa: не настроен (демо-режим)")
    logging.info("Проверка голосового модуля...")
    from ai_talent_bot.utils.voice import is_voice_available
    if is_voice_available():
        logging.info("Vosk: голосовой ввод доступен ✅")
    else:
        logging.warning("Vosk: голосовой ввод НЕДОСТУПЕН (запустите scripts/download_model.sh)")
    logging.info("Бот запущен!")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    # Голосовой роутер — перехватывает голос ДО остальных хэндлеров
    dp.include_router(voice.router)
    dp.include_router(onboarding.router)
    dp.include_router(profile.router)
    dp.include_router(orders.router)
    dp.include_router(applications.router)
    dp.include_router(search.router)
    dp.include_router(payments.router)

    dp.startup.register(on_startup)

    # Запуск
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
