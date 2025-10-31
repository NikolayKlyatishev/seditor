# -*- coding: utf-8 -*-
"""
Утилиты для работы с файлами и директориями
"""

import os
from pathlib import Path
from typing import List, Tuple


def scan_directory(directory: str) -> List[Tuple[str, bool, str]]:
    """
    Сканировать директорию и получить список файлов и директорий

    Args:
        directory: Путь к директории для сканирования

    Returns:
        Список кортежей (имя, is_directory, полный_путь)
    """
    items = []
    try:
        for item in sorted(os.listdir(directory)):
            # Пропускаем скрытые файлы (начинающиеся с .)
            if item.startswith('.'):
                continue

            full_path = os.path.join(directory, item)
            is_dir = os.path.isdir(full_path)

            items.append((item, is_dir, full_path))
    except PermissionError:
        # Нет прав для чтения директории
        pass

    # Сортировка: сначала директории, потом файлы
    items.sort(key=lambda x: (not x[1], x[0].lower()))

    return items


def is_directory(path: str) -> bool:
    """Проверить, является ли путь директорией"""
    return os.path.isdir(path)


def is_file(path: str) -> bool:
    """Проверить, является ли путь файлом"""
    return os.path.isfile(path)


def get_parent_directory(path: str) -> str:
    """Получить родительскую директорию"""
    return os.path.dirname(os.path.abspath(path))


def normalize_path(path: str) -> str:
    """Нормализовать путь (разрешить . и ..)"""
    return os.path.normpath(os.path.abspath(path))


def delete_file(path: str) -> bool:
    """
    Удалить файл или директорию

    Args:
        path: Путь к файлу

    Returns:
        True если файл успешно удалён, False иначе
    """
    try:
        if os.path.isdir(path):
            os.rmdir(path)  # Удаление пустой директории
        else:
            os.remove(path)  # Удаление файла
        return True
    except (OSError, PermissionError):
        return False
