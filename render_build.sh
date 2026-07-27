#!/bin/bash
# Render build script — installs Python deps + builds React frontend
set -e

echo "=== Installing Python dependencies ==="
pip install --no-cache-dir \
    "aiogram>=3.10,<4.0" \
    "aiosqlite>=0.20.0" \
    "python-dotenv>=1.0.0" \
    "aiohttp>=3.9.0" \
    "fastapi>=0.110.0" \
    "uvicorn>=0.27.0"

# The repo root IS the ai_talent_bot package (__init__.py, config.py, handlers/ etc)
# On Render it's cloned to /opt/render/project/src/ — create symlink so imports work
if [ ! -e "ai_talent_bot" ]; then
    ln -sf . ai_talent_bot
fi

# Build React Mini App frontend (if npm is available)
echo "=== Building Mini App frontend ==="
if [ -d "mini_app/frontend" ]; then
    cd mini_app/frontend

    if command -v npm &> /dev/null; then
        echo "npm found: $(npm --version)"
        npm install --legacy-peer-deps 2>&1 | tail -3
        npm run build 2>&1 | tail -5
        echo "Frontend built successfully!"
    else
        echo "npm not available — using pre-built dist/ from repo"
    fi

    if [ ! -d "dist" ]; then
        echo "ERROR: No dist/ directory! Frontend will not work."
    else
        echo "dist/ exists: $(ls dist/ 2>/dev/null | wc -l) files"
    fi

    cd /opt/render/project/src 2>/dev/null || cd ../..
else
    echo "WARNING: mini_app/frontend directory not found"
fi

echo "=== Build complete ==="
