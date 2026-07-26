#!/bin/bash
# Render start script
set -e

# PYTHONPATH = repo root (where ai_talent_bot/ package lives)
export PYTHONPATH="$(pwd):${PYTHONPATH}"
mkdir -p data

exec python3 -m uvicorn ai_talent_bot.mini_app.backend.main:app \
    --host 0.0.0.0 --port "${PORT:-8000}"
