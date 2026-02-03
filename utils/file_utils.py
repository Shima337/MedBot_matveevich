"""
Утилиты для работы с файлами
"""
import base64
import io
from PIL import Image
from typing import Optional, Tuple
import aiofiles
import os


async def image_to_base64(image_path: str) -> str:
    """Конвертация изображения в base64 строку"""
    async with aiofiles.open(image_path, 'rb') as f:
        image_data = await f.read()
        return base64.b64encode(image_data).decode('utf-8')


def get_image_mime_type(image_path: str) -> str:
    """Определение MIME типа изображения"""
    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    return mime_types.get(ext, 'image/jpeg')


async def save_file_from_bytes(file_bytes: bytes, file_path: str):
    """Сохранение файла из байтов"""
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_bytes)


def is_image_file(file_path: str) -> bool:
    """Проверка, является ли файл изображением"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    ext = os.path.splitext(file_path)[1].lower()
    return ext in image_extensions


def is_document_file(file_path: str) -> bool:
    """Проверка, является ли файл документом"""
    document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf'}
    ext = os.path.splitext(file_path)[1].lower()
    return ext in document_extensions
