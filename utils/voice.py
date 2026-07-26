"""Распознавание голосовых сообщений (Vosk + ffmpeg)."""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

# ── Vosk ──────────────────────────────────────────────────────
# Модель скачивается отдельно: см. README / scripts/download_model.sh
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "vosk-model-small-ru"

_vosk_available = False
try:
    from vosk import Model, KaldiRecognizer
    if MODEL_DIR.exists():
        _model = Model(str(MODEL_DIR))
        _vosk_available = True
        logger.info("Vosk модель загружена: %s", MODEL_DIR)
    else:
        logger.warning("Vosk модель не найдена: %s", MODEL_DIR)
except ImportError:
    logger.warning("vosk не установлен — голосовой ввод недоступен")


def is_voice_available() -> bool:
    return _vosk_available


async def download_voice(bot, file_id: str) -> bytes | None:
    """Скачать голосовое сообщение из Telegram."""
    try:
        file = await bot.get_file(file_id)
        file_path = file.file_path

        url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        return None
    except Exception as e:
        logger.error("Ошибка скачивания голосового: %s", e)
        return None


def _ogg_to_wav(ogg_data: bytes) -> bytes | None:
    """Конвертировать OGG (Telegram) → WAV 16kHz mono (Vosk)."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_f:
            ogg_f.write(ogg_data)
            ogg_path = ogg_f.name

        wav_path = ogg_path.replace(".ogg", ".wav")

        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", ogg_path,
                "-ar", "16000",    # 16 kHz
                "-ac", "1",        # mono
                "-f", "wav",
                wav_path,
            ],
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error("ffmpeg ошибка: %s", result.stderr.decode())
            return None

        wav_data = Path(wav_path).read_bytes()

        # Чистим временные файлы
        Path(ogg_path).unlink(missing_ok=True)
        Path(wav_path).unlink(missing_ok=True)

        return wav_data
    except FileNotFoundError:
        logger.error("ffmpeg не найден! Установите: apt install ffmpeg")
        return None
    except Exception as e:
        logger.error("Ошибка конвертации OGG→WAV: %s", e)
        return None


def transcribe(wav_data: bytes) -> str | None:
    """Распознать WAV-аудио через Vosk."""
    if not _vosk_available:
        return None

    try:
        rec = KaldiRecognizer(_model, 16000)
        rec.SetWords(True)

        # Читаем аудио чанками
        results = []
        chunk_size = 4000
        for i in range(0, len(wav_data), chunk_size):
            chunk = wav_data[i:i + chunk_size]
            if rec.AcceptWaveform(chunk):
                result = json.loads(rec.Result())
                if result.get("text"):
                    results.append(result["text"])

        # Финальный результат
        final = json.loads(rec.FinalResult())
        if final.get("text"):
            results.append(final["text"])

        text = " ".join(results).strip()
        return text if text else None
    except Exception as e:
        logger.error("Ошибка распознавания Vosk: %s", e)
        return None


async def process_voice_message(bot, file_id: str) -> str | None:
    """
    Полный цикл: скачать → сконвертировать → распознать.
    Возвращает текст или None.
    """
    if not _vosk_available:
        return None

    ogg_data = await download_voice(bot, file_id)
    if not ogg_data:
        return None

    wav_data = _ogg_to_wav(ogg_data)
    if not wav_data:
        return None

    return transcribe(wav_data)
