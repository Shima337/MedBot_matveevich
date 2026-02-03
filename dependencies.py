"""
Модуль для хранения зависимостей бота
"""
from typing import Optional
from database import Database
from openai_client import OpenAIClient

# Глобальные переменные для зависимостей (инициализируются в bot.py)
db: Optional[Database] = None
openai_client: Optional[OpenAIClient] = None
