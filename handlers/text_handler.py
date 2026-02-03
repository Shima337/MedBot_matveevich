"""
Обработчик текстовых сообщений
"""
from aiogram import Router, F
from aiogram.types import Message
import dependencies
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user_text = message.text
    db, openai_client = dependencies.db, dependencies.openai_client

    # Проверяем, что зависимости инициализированы
    if db is None or openai_client is None:
        logger.error("Зависимости не инициализированы: db или openai_client = None")
        await message.answer("Бот еще не готов. Подождите немного и попробуйте снова.")
        return
    
    try:
        logger.info(f"Получено текстовое сообщение от пользователя {user_id}: {user_text[:50]}")
        
        # Сохраняем сообщение пользователя в БД
        await db.save_message(user_id, "user", user_text)
        logger.info("Сообщение сохранено в БД")
        
        # Загружаем историю диалога
        conversation_history = await db.get_conversation_history(user_id)
        logger.info(f"Загружена история диалога: {len(conversation_history)} сообщений")
        
        # Отправляем в OpenAI API (gpt-5.2)
        logger.info("Отправляю запрос в OpenAI API...")
        response = await openai_client.send_text_message(conversation_history)
        logger.info(f"Получен ответ от OpenAI: {response[:100]}")
        
        # Сохраняем ответ в БД
        await db.save_message(user_id, "assistant", response)
        
        # Отправляем ответ пользователю
        await message.answer(response)
        logger.info("Ответ отправлен пользователю")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке текстового сообщения: {str(e)}", exc_info=True)
        error_msg = f"Извините, произошла ошибка: {str(e)[:200]}"
        await message.answer(error_msg)
