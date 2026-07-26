#!/bin/bash
# Render build script — installs Python dependencies
# Frontend is pre-built (dist/ committed in repo)
set -e

echo "=== Installing Python dependencies ==="
pip install --no-cache-dir \
    "aiogram>=3.10,<4.0" \
    "aiosqlite>=0.20.0" \
    "python-dotenv>=1.0.0" \
    "aiohttp>=3.9.0" \
    "fastapi>=0.110.0" \
    "uvicorn>=0.27.0"

echo "=== Build complete ==="
