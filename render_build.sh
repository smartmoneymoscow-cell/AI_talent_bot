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

# Build React Mini App frontend
echo "=== Building Mini App frontend ==="
PROJECT_ROOT=$(pwd)
if [ -d "mini_app/frontend" ]; then
    cd mini_app/frontend

    # Install Node.js if not present (Render Python env may not have it)
    if ! command -v node &> /dev/null; then
        echo "Node.js not found — installing..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>/dev/null || true
        apt-get install -y nodejs 2>/dev/null || {
            echo "Trying nvm approach..."
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
            nvm install 20 2>/dev/null || true
        }
    fi

    if command -v npm &> /dev/null; then
        echo "npm found: $(npm --version)"
        npm install --legacy-peer-deps
        npm run build
        echo "Frontend built successfully!"
        ls -la dist/ 2>/dev/null || echo "WARNING: dist/ not created"
    else
        echo "WARNING: npm not available. Using pre-built dist/ from repo."
        if [ ! -d "dist" ]; then
            echo "ERROR: No dist/ directory and can't build frontend!"
        fi
    fi

    cd "$PROJECT_ROOT"
else
    echo "WARNING: mini_app/frontend directory not found"
fi

echo "=== Build complete ==="
