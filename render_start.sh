#!/bin/bash
# Render start script — serves FastAPI backend + static frontend
set -e

# Ensure data directory exists (absolute path matching DB_PATH)
mkdir -p /opt/render/project/src/data

# Ensure ai_talent_bot package is importable
[ ! -e "ai_talent_bot" ] && ln -sf . ai_talent_bot

# Log environment status (without revealing secrets)
echo "=== Environment check ==="
echo "BOT_TOKEN: $([ -n \"$BOT_TOKEN\" ] && echo 'set' || echo '⚠️ NOT SET')"
echo "MINI_APP_URL: ${MINI_APP_URL:-⚠️ NOT SET}"
echo "DB_PATH: ${DB_PATH:-data/bot.db}"
echo "PORT: ${PORT:-8000}"

# Check frontend
if [ -d "mini_app/frontend/dist" ]; then
    echo "Frontend dist: ✅ found"
else
    echo "Frontend dist: ⚠️ NOT FOUND"
fi

echo "=== Starting server ==="
exec python3 -m uvicorn server:app --host 0.0.0.0 --port "${PORT:-8000}"
