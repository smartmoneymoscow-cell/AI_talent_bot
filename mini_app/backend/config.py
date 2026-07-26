"""Конфигурация бота."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Database
    DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "data" / "bot.db"))

    # YooKassa (платежи для самозанятых)
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")

    # Комиссия платформы (в процентах)
    PLATFORM_FEE_PERCENT: float = float(os.getenv("PLATFORM_FEE_PERCENT", "5"))

    # Админы (через запятую)
    ADMIN_IDS: list[int] = field(default_factory=list)

    # Mini App URL
    MINI_APP_URL: str = os.getenv("MINI_APP_URL", "")

    def __post_init__(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        raw = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
        Path(self.DB_PATH).parent.mkdir(parents=True, exist_ok=True)


config = Config()
