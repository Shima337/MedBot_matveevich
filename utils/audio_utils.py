"""
Утилиты для работы с аудио файлами.
Голосовые в Telegram приходят в OGG; Whisper API принимает mp3, wav, m4a и др., но не OGG.
Конвертация через ffmpeg (нужно установить: brew install ffmpeg).
"""
import os
import asyncio
import shutil
import tempfile
from typing import Optional


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


async def convert_ogg_to_mp3_ffmpeg(ogg_path: str, output_path: Optional[str] = None) -> str:
    """
    Конвертация OGG в MP3 через ffmpeg (без pydub).
    Требует установленный ffmpeg: brew install ffmpeg
    """
    if not _ffmpeg_available():
        raise RuntimeError(
            "Для голосовых сообщений нужен ffmpeg. "
            "Установите: brew install ffmpeg (Mac) или apt install ffmpeg (Linux)."
        )
    if output_path is None:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        output_path = f.name
        f.close()
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", ogg_path, "-acodec", "libmp3lame", "-q:a", "2", output_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        err = stderr.decode("utf-8", errors="replace") if stderr else "unknown"
        raise RuntimeError(f"Ошибка конвертации аудио (ffmpeg): {err[:300]}")
    return output_path


async def convert_audio_for_whisper(audio_path: str) -> str:
    """
    Конвертация аудио в формат для Whisper API.
    Поддерживаемые форматы: mp3, mp4, mpeg, mpga, m4a, wav, webm.
    Telegram присылает OGG — конвертируем в MP3 через ffmpeg.
    """
    ext = os.path.splitext(audio_path)[1].lower()
    supported = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
    if ext in supported:
        return audio_path
    if ext == ".ogg":
        return await convert_ogg_to_mp3_ffmpeg(audio_path)
    # Остальные форматы — пробуем через ffmpeg как «любой вход» -> mp3
    if _ffmpeg_available():
        out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", audio_path, "-acodec", "libmp3lame", "-q:a", "2", out_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
    raise RuntimeError(
        "Не удалось конвертировать аудио. Установите ffmpeg: brew install ffmpeg"
    )
