#!/bin/bash
# Render start script
set -e

# Create data directory for SQLite
mkdir -p data

# Start the FastAPI server
cd mini_app/backend
exec python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
