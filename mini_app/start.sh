#!/bin/bash
# Запуск Mini App (backend + frontend)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 AI Talent Hub — Mini App"
echo ""

# 1. Сборка фронтенда
echo "📦 Сборка фронтенда..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "   Установка зависимостей..."
    npm install 2>&1 | tail -3
fi
npm run build 2>&1 | tail -5
cd ..
echo "✅ Фронтенд собран"

# 2. Запуск бэкенда
echo "🖥  Запуск FastAPI бэкенда..."
echo "   URL: http://localhost:8000"
echo ""
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
