"""
Обработчик голосовых сообщений.
Telegram присылает OGG/Opus — отправляем в Whisper как есть, без конвертации.
"""
import logging
import os
import tempfile
import uuid

from aiogram import Router, F
from aiogram.types import Message

import dependencies

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.voice | F.audio)
async def handle_voice_message(message: Message):
    """Обработка голосовых: скачать OGG → Whisper → ответ от gpt-5.2."""
    user_id = message.from_user.id
    db, openai_client = dependencies.db, dependencies.openai_client
    if db is None or openai_client is None:
        await message.answer("Бот еще не готов. Подождите немного и попробуйте снова.")
        return

    local_file_path = None
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        bot = message.bot
        file = await bot.get_file(file_id)
        file_path = file.file_path

        safe_id = (file_id or "").replace("/", "_")[:64]
        temp_dir = tempfile.gettempdir()
        local_file_path = os.path.join(temp_dir, f"voice_{safe_id}_{uuid.uuid4().hex[:8]}.ogg")
        await bot.download_file(file_path, local_file_path)
        if not os.path.exists(local_file_path) or os.path.getsize(local_file_path) == 0:
            raise RuntimeError("Файл голоса не скачался или пустой")

        logger.info("Голос скачан %s байт, отправляю в Whisper (OGG как есть)...", os.path.getsize(local_file_path))
        conversation_history = await db.get_conversation_history(user_id)
        response = await openai_client.process_voice_message(local_file_path, conversation_history)

        await db.save_message(user_id, "user", "[Голосовое сообщение]")
        await db.save_message(user_id, "assistant", response)
        await message.answer(response)

    except Exception as e:
        err = str(e)
        logger.error("Голос: %s", err, exc_info=True)
        await message.answer(f"Ошибка голоса: {err[:400]}")
    finally:
        if local_file_path and os.path.exists(local_file_path):
            try:
                os.remove(local_file_path)
            except OSError:
                pass
