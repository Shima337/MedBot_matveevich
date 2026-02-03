"""
Работа с базой данных SQLite для хранения истории диалогов и данных пользователя
"""
import sqlite3
import aiosqlite
from typing import List, Dict, Optional
from datetime import datetime
import json


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных - создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица для истории диалогов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для данных пользователя
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id INTEGER PRIMARY KEY,
                    height REAL,
                    weight REAL,
                    preferences TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Индекс для быстрого поиска по user_id
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
                ON conversations(user_id, created_at)
            """)
            
            await db.commit()

    async def save_message(self, user_id: int, role: str, content: str):
        """Сохранение сообщения в историю диалога"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO conversations (user_id, role, content)
                VALUES (?, ?, ?)
            """, (user_id, role, content))
            await db.commit()

    async def get_conversation_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Получение истории диалога пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT role, content 
                FROM conversations 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                # Возвращаем в обратном порядке (старые сообщения первыми)
                return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    async def clear_conversation_history(self, user_id: int):
        """Очистка истории диалога пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM conversations WHERE user_id = ?
            """, (user_id,))
            await db.commit()

    async def save_user_data(self, user_id: int, height: Optional[float] = None, 
                           weight: Optional[float] = None, preferences: Optional[Dict] = None):
        """Сохранение данных пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, существует ли запись
            async with db.execute("""
                SELECT user_id FROM user_data WHERE user_id = ?
            """, (user_id,)) as cursor:
                exists = await cursor.fetchone()
            
            preferences_json = json.dumps(preferences) if preferences else None
            
            if exists:
                # Обновляем существующую запись
                update_fields = []
                params = []
                if height is not None:
                    update_fields.append("height = ?")
                    params.append(height)
                if weight is not None:
                    update_fields.append("weight = ?")
                    params.append(weight)
                if preferences_json is not None:
                    update_fields.append("preferences = ?")
                    params.append(preferences_json)
                
                if update_fields:
                    update_fields.append("updated_at = CURRENT_TIMESTAMP")
                    params.append(user_id)
                    await db.execute(f"""
                        UPDATE user_data 
                        SET {', '.join(update_fields)}
                        WHERE user_id = ?
                    """, params)
            else:
                # Создаем новую запись
                await db.execute("""
                    INSERT INTO user_data (user_id, height, weight, preferences)
                    VALUES (?, ?, ?, ?)
                """, (user_id, height, weight, preferences_json))
            
            await db.commit()

    async def get_user_data(self, user_id: int) -> Optional[Dict]:
        """Получение данных пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT height, weight, preferences 
                FROM user_data 
                WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "height": row["height"],
                        "weight": row["weight"],
                        "preferences": json.loads(row["preferences"]) if row["preferences"] else None
                    }
                return None
