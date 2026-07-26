"""
Автопинг для предотвращения засыпания Render Free Tier.
Render засыпает через 15 мин бездействия — пингуем каждые 3 минуты.

Запуск:
  python3 mini_app/backend/keep_alive.py [URL]

По умолчанию пингует localhost:8000.
"""
import sys
import time
import logging
import urllib.request
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PING] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_URL = "https://ai-talent-bot.onrender.com/api/me"
PING_INTERVAL = 180  # 3 минуты


def ping(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "KeepAlive/1.0")
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            logger.info(f"✅ {url} → {status}")
            return status < 500
    except Exception as e:
        logger.warning(f"⚠️ {url} → {e}")
        return False


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    logger.info(f"🚀 Keep-alive started: {url}")
    logger.info(f"   Interval: {PING_INTERVAL}s ({PING_INTERVAL // 60} min)")

    while True:
        ping(url)
        time.sleep(PING_INTERVAL)


if __name__ == "__main__":
    main()
