#!/bin/bash
# Скачивание модели Vosk для русского языка (~50 МБ)
set -e

MODEL_DIR="models"
MODEL_NAME="vosk-model-small-ru-0.22"
MODEL_URL="https://alphacephei.com/vosk/models/${MODEL_NAME}.zip"

cd "$(dirname "$0")/.."

echo "📦 Скачивание модели Vosk (русский, ~50 МБ)..."
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

if [ -d "$MODEL_NAME" ]; then
    echo "✅ Модель уже существует: $MODEL_NAME"
    exit 0
fi

curl -L -o "${MODEL_NAME}.zip" "$MODEL_URL"
echo "📂 Распаковка..."
unzip -q "${MODEL_NAME}.zip"
rm "${MODEL_NAME}.zip"

# Создаём симлинк для удобства
ln -sfn "$MODEL_NAME" "vosk-model-small-ru"

echo "✅ Модель установлена: $MODEL_DIR/$MODEL_NAME"
echo "   Симлинк: $MODEL_DIR/vosk-model-small-ru"
