"""
Обработчики сообщений
"""
from .text_handler import router as text_router
from .file_handler import router as file_router
from .voice_handler import router as voice_router

__all__ = ['text_router', 'file_router', 'voice_router']
