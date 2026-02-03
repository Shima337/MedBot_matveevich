"""
Обработчик файлов (изображения, документы)
"""
from aiogram import Router, F
from aiogram.types import Message
import dependencies
from utils.file_utils import is_image_file, is_document_file
from utils.document_utils import extract_text_from_document
import logging
import tempfile
import os

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.photo | F.document)
async def handle_file_message(message: Message):
    """Обработка файлов (изображения и документы)"""
    user_id = message.from_user.id
    
    db, openai_client = dependencies.db, dependencies.openai_client
    # Проверяем, что зависимости инициализированы
    if db is None or openai_client is None:
        logger.error("Зависимости не инициализированы: db или openai_client = None")
        await message.answer("Бот еще не готов. Подождите немного и попробуйте снова.")
        return

    try:
        # Определяем тип файла и получаем file_id
        if message.photo:
            # Фото - берем самое большое разрешение
            file_id = message.photo[-1].file_id
            file_type = "image"
        elif message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name or "file"
            file_type = "document" if is_document_file(file_name) else "other"
            if is_image_file(file_name):
                file_type = "image"
        else:
            await message.answer("Не удалось определить тип файла.")
            return
        
        # Получаем информацию о файле
        bot = message.bot
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Создаем временный файл для сохранения
        temp_dir = tempfile.gettempdir()
        # Используем уникальное имя файла
        import uuid
        file_extension = os.path.splitext(file_path)[1] or '.jpg'
        local_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}{file_extension}")
        
        # Скачиваем файл
        logger.info(f"Скачиваю файл: {file_path} -> {local_file_path}")
        await bot.download_file(file_path, local_file_path)
        
        # Проверяем, что файл скачался
        if not os.path.exists(local_file_path):
            raise Exception("Файл не был скачан")
        
        file_size = os.path.getsize(local_file_path)
        logger.info(f"Файл скачан: {local_file_path}, размер: {file_size} байт")
        
        try:
            if file_type == "image":
                # Обработка изображения
                user_caption = message.caption or "Что на этом изображении?"
                conversation_history = await db.get_conversation_history(user_id)
                
                # Сохраняем сообщение пользователя
                await db.save_message(user_id, "user", f"[Изображение]: {user_caption}")
                
                logger.info(f"Отправляю изображение в OpenAI API: {local_file_path}")
                # Отправляем в OpenAI Vision API (gpt-5.2)
                response = await openai_client.send_image_message(
                    local_file_path, 
                    user_caption,
                    conversation_history
                )
                
                # Сохраняем ответ
                await db.save_message(user_id, "assistant", response)
                
                # Отправляем ответ пользователю
                await message.answer(response)
                
            elif file_type == "document":
                # Обработка документа
                user_message = message.caption or ""
                conversation_history = await db.get_conversation_history(user_id)
                
                # Извлекаем текст из документа
                document_text = await extract_text_from_document(local_file_path)
                
                if document_text:
                    # Сохраняем сообщение пользователя
                    await db.save_message(user_id, "user", f"[Документ]: {user_message}")
                    
                    # Отправляем в OpenAI API (gpt-5.2)
                    response = await openai_client.process_document(
                        document_text,
                        user_message,
                        conversation_history
                    )
                    
                    # Сохраняем ответ
                    await db.save_message(user_id, "assistant", response)
                    
                    # Отправляем ответ пользователю
                    await message.answer(response)
                else:
                    await message.answer("Не удалось извлечь текст из документа. Поддерживаются форматы: PDF, DOCX, TXT.")
                    
            else:
                await message.answer("Этот тип файла пока не поддерживается. Отправьте изображение или документ (PDF, DOCX, TXT).")
                
        finally:
            # Удаляем временный файл
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
                
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {str(e)}", exc_info=True)
        error_message = f"Извините, произошла ошибка при обработке файла: {str(e)}"
        await message.answer(error_message[:500])  # Ограничиваем длину сообщения
