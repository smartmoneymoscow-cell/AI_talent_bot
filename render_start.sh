#!/bin/bash
# Render start script — serves FastAPI backend + static frontend
set -e

# Ensure data directory exists (absolute path matching DB_PATH)
mkdir -p /opt/render/project/src/data

# Start the FastAPI server from project root
exec python3 -m uvicorn server:app --host 0.0.0.0 --port "${PORT:-8000}"
