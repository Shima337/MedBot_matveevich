"""
Основной файл Telegram бота
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_TOKEN, DB_PATH
from database import Database
from openai_client import OpenAIClient
from dependencies import db, openai_client
from handlers import text_router, file_router, voice_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def start_command(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "пользователь"
    
    welcome_text = f"""Привет, {user_name}!

Я твой помощник по образу жизни. Я помогу тебе улучшить самочувствие, уменьшить живот и снизить влияние еды на сахар через небольшие, понятные изменения привычек.

Я могу:
• Принимать текстовые сообщения
• Анализировать изображения
• Обрабатывать голосовые сообщения
• Читать документы (PDF, DOCX, TXT)

Просто напиши мне или отправь файл, и я помогу тебе!"""
    
    await message.answer(welcome_text)
    
    # Инициализируем данные пользователя, если их еще нет
    import dependencies
    user_data = await dependencies.db.get_user_data(user_id)
    if not user_data:
        await dependencies.db.save_user_data(user_id)


async def reset_command(message: Message):
    """Обработчик команды /reset - сброс истории диалога"""
    import dependencies
    user_id = message.from_user.id
    await dependencies.db.clear_conversation_history(user_id)
    await message.answer("История диалога очищена. Начнем заново!")


async def main():
    """Основная функция запуска бота"""
    # Импортируем модуль зависимостей для установки значений
    import dependencies
    
    # Проверка токена
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не установлен в переменных окружения")
        return
    
    # Инициализация хранилища FSM
    storage = MemoryStorage()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # Инициализация базы данных
    dependencies.db = Database(DB_PATH)
    await dependencies.db.init_db()
    logger.info("База данных инициализирована")
    
    # Инициализация OpenAI клиента
    try:
        dependencies.openai_client = OpenAIClient()
        logger.info(f"OpenAI клиент инициализирован с моделью: {dependencies.openai_client.model}")
    except Exception as e:
        logger.error(f"Ошибка инициализации OpenAI клиента: {str(e)}")
        return
    
    # Регистрация команд
    dp.message.register(start_command, Command("start"))
    dp.message.register(reset_command, Command("reset"))
    
    # Регистрация роутеров
    dp.include_router(text_router)
    dp.include_router(file_router)
    dp.include_router(voice_router)
    
    logger.info("Бот запущен и готов к работе")
    
    # Запуск бота
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {str(e)}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
