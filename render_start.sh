#!/bin/bash
# Render start script
set -e
export PYTHONPATH="${PWD}:${PYTHONPATH}"
mkdir -p data
python3 -m uvicorn ai_talent_bot.mini_app.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
