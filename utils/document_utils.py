"""
Утилиты для извлечения текста из документов
"""
import os
from typing import Optional


async def extract_text_from_pdf(pdf_path: str) -> str:
    """Извлечение текста из PDF файла"""
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Ошибка при извлечении текста из PDF: {str(e)}")


async def extract_text_from_docx(docx_path: str) -> str:
    """Извлечение текста из DOCX файла"""
    try:
        from docx import Document
        doc = Document(docx_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise Exception(f"Ошибка при извлечении текста из DOCX: {str(e)}")


async def extract_text_from_txt(txt_path: str) -> str:
    """Извлечение текста из TXT файла"""
    try:
        import aiofiles
        async with aiofiles.open(txt_path, 'r', encoding='utf-8') as f:
            text = await f.read()
        return text.strip()
    except Exception as e:
        raise Exception(f"Ошибка при чтении TXT файла: {str(e)}")


async def extract_text_from_document(file_path: str) -> Optional[str]:
    """
    Извлечение текста из документа по типу файла
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        Текст документа или None, если формат не поддерживается
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return await extract_text_from_pdf(file_path)
    elif ext in ['.doc', '.docx']:
        return await extract_text_from_docx(file_path)
    elif ext == '.txt':
        return await extract_text_from_txt(file_path)
    else:
        return None
