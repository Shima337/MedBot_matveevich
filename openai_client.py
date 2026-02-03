"""
Клиент для работы с OpenAI API
ВАЖНО: Использовать модель gpt-5.2 во всех запросах
"""
import os
import base64
from typing import List, Dict, Optional
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, SYSTEM_PROMPT
from utils.file_utils import image_to_base64, get_image_mime_type


class OpenAIClient:
    def __init__(self):
        """Инициализация клиента OpenAI"""
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY не установлен в переменных окружения")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL  # gpt-5.2
        self.system_prompt = SYSTEM_PROMPT

    async def send_text_message(self, messages: List[Dict[str, str]]) -> str:
        """
        Отправка текстового сообщения в gpt-5.2
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "текст"}]
        
        Returns:
            Ответ от модели
        """
        # Добавляем системный промпт в начало
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,  # gpt-5.2
                messages=full_messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Ошибка при обращении к OpenAI API: {str(e)}")

    async def send_image_message(self, image_path: str, user_message: str, 
                                conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Отправка изображения с текстом в gpt-5.2 (vision)
        
        Args:
            image_path: Путь к изображению
            user_message: Текстовое сообщение пользователя
            conversation_history: История диалога (опционально)
        
        Returns:
            Ответ от модели
        """
        # Конвертируем изображение в base64
        base64_image = await image_to_base64(image_path)
        mime_type = get_image_mime_type(image_path)
        
        # Формируем сообщение с изображением
        image_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_message
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}"
                    }
                }
            ]
        }
        
        # Добавляем системный промпт и историю
        messages = [{"role": "system", "content": self.system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append(image_message)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,  # gpt-5.2
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Ошибка при обращении к OpenAI Vision API: {str(e)}\n{error_details}")
            raise Exception(f"Ошибка при обращении к OpenAI Vision API: {str(e)}")

    def _transcribe_file_sync(self, audio_path: str) -> str:
        """Синхронный вызов Whisper API по пути к файлу."""
        with open(audio_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        return transcript.text or ""

    async def transcribe_audio(self, audio_path: str) -> str:
        """
        Транскрипция через Whisper API.
        Сначала пробуем OGG (Telegram). При ошибке формата — конвертируем в MP3 через ffmpeg и повторяем.
        """
        import logging
        import asyncio
        from utils.audio_utils import convert_ogg_to_mp3_ffmpeg

        log = logging.getLogger(__name__)
        if not os.path.exists(audio_path):
            raise Exception(f"Файл не найден: {audio_path}")
        size = os.path.getsize(audio_path)
        log.info("Whisper: отправляю %s (%s байт)", audio_path, size)

        loop = asyncio.get_event_loop()
        try:
            text = await loop.run_in_executor(None, self._transcribe_file_sync, audio_path)
            log.info("Whisper вернул: %s", (text[:80] + "...") if len(text) > 80 else text)
            return text
        except Exception as e:
            err = str(e).lower()
            # Формат не подходит — конвертируем OGG → MP3 и повторяем
            if "format" in err or "ogg" in err or "unsupported" in err or "file type" in err:
                log.info("Whisper не принял OGG, конвертирую в MP3 через ffmpeg...")
                try:
                    mp3_path = await convert_ogg_to_mp3_ffmpeg(audio_path)
                    try:
                        text = await loop.run_in_executor(None, self._transcribe_file_sync, mp3_path)
                        log.info("Whisper (после MP3) вернул: %s", (text[:80] + "...") if len(text) > 80 else text)
                        return text
                    finally:
                        if mp3_path != audio_path and os.path.exists(mp3_path):
                            try:
                                os.remove(mp3_path)
                            except OSError:
                                pass
                except Exception as conv_e:
                    log.exception("Конвертация или повторная транскрипция: %s", conv_e)
                    raise Exception(f"Транскрипция не удалась: {conv_e}")
            log.exception("Whisper API ошибка")
            raise Exception(f"Ошибка при транскрипции аудио: {str(e)}")

    async def process_voice_message(self, audio_path: str, 
                                    conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Обработка голосового сообщения: транскрипция + отправка в gpt-5.2
        
        Args:
            audio_path: Путь к аудио файлу
            conversation_history: История диалога (опционально)
        
        Returns:
            Ответ от модели
        """
        # Сначала транскрибируем аудио
        transcribed_text = await self.transcribe_audio(audio_path)
        
        # Затем отправляем транскрипцию в gpt-5.2
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": f"[Голосовое сообщение]: {transcribed_text}"})
        
        return await self.send_text_message(messages)

    async def process_document(self, document_text: str, user_message: str = "",
                             conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Обработка документа: извлеченный текст отправляется в gpt-5.2
        
        Args:
            document_text: Текст из документа
            user_message: Дополнительное сообщение пользователя
            conversation_history: История диалога (опционально)
        
        Returns:
            Ответ от модели
        """
        # Формируем сообщение с текстом документа
        content = f"{user_message}\n\n[Содержимое документа]:\n{document_text}" if user_message else f"[Содержимое документа]:\n{document_text}"
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": content})
        
        return await self.send_text_message(messages)
