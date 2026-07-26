#!/bin/bash
# Render build script — builds frontend + installs backend deps
set -e

echo "=== Installing Python dependencies ==="
pip install --no-cache-dir \
    "aiogram>=3.10,<4.0" \
    "aiosqlite>=0.20.0" \
    "python-dotenv>=1.0.0" \
    "aiohttp>=3.9.0" \
    "fastapi>=0.110.0" \
    "uvicorn>=0.27.0"

echo "=== Installing Node.js ==="
# Render provides Node, but ensure it's available
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "=== Building React Mini App frontend ==="
cd mini_app/frontend
npm ci
npm run build
cd ../..

echo "=== Build complete ==="
