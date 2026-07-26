#!/bin/bash
# Render start script — serves FastAPI backend + static frontend
set -e

# Ensure data directory exists (absolute path matching DB_PATH)
mkdir -p /opt/render/project/src/data

# Ensure ai_talent_bot package is importable
[ ! -e "ai_talent_bot" ] && ln -sf . ai_talent_bot

# Start the FastAPI server from project root
exec python3 -m uvicorn server:app --host 0.0.0.0 --port "${PORT:-8000}"
