# -*- coding: utf-8 -*-
"""
Структура данных для дерева файлов
"""

import os
from typing import Optional, List
from seditor.utils.file_utils import scan_directory, normalize_path


class FileNode:
    """Узел дерева файлов"""

    def __init__(self, name: str, path: str, is_dir: bool, parent: Optional['FileNode'] = None):
        """
        Инициализация узла

        Args:
            name: Имя файла/директории
            path: Полный путь
            is_dir: True если директория, False если файл
            parent: Родительский узел
        """
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.parent = parent
        self.children: List['FileNode'] = []
        self.expanded = False  # Развёрнута ли директория
        self.scanned = False  # Сканировались ли дети

    def get_depth(self) -> int:
        """Получить уровень вложенности узла (0 - корень)"""
        depth = 0
        node = self.parent
        while node:
            depth += 1
            node = node.parent
        return depth

    def scan_children(self) -> None:
        """Сканировать дочерние элементы"""
        if not self.is_dir or self.scanned:
            return

        try:
            items = scan_directory(self.path)
            self.children = [
                FileNode(name=name, path=full_path, is_dir=is_dir, parent=self)
                for name, is_dir, full_path in items
            ]
            self.scanned = True
        except (PermissionError, OSError):
            self.children = []
            self.scanned = True

    def expand(self) -> None:
        """Развернуть директорию"""
        if self.is_dir:
            if not self.scanned:
                self.scan_children()
            self.expanded = True

    def collapse(self) -> None:
        """Свернуть директорию"""
        if self.is_dir:
            self.expanded = False

    def toggle(self) -> None:
        """Переключить состояние развёрнутости"""
        if self.expanded:
            self.collapse()
        else:
            self.expand()


class FileTree:
    """Дерево файлов"""

    def __init__(self, root_path: str):
        """
        Инициализация дерева файлов

        Args:
            root_path: Путь к корневой директории
        """
        normalized_path = normalize_path(root_path)
        if not os.path.isdir(normalized_path):
            normalized_path = os.getcwd()

        # Создаём корневой узел
        self.root = FileNode(name=os.path.basename(normalized_path) or normalized_path,
                            path=normalized_path,
                            is_dir=True)
        self.root.expand()  # Корневая директория развёрнута по умолчанию

        self.current_path = normalized_path
        self.selected_index = 0  # Индекс выбранного элемента в плоском списке

    def get_visible_items(self) -> List[FileNode]:
        """
        Получить список видимых элементов (все развёрнутые узлы в дереве)
        
        Returns:
            Список узлов с информацией о глубине вложенности
        """
        result = []
        
        def collect_visible(node: FileNode):
            """Рекурсивно собрать все видимые узлы"""
            # Добавляем все дочерние узлы текущего узла
            for child in node.children:
                result.append(child)
                # Если директория развёрнута, добавляем её детей
                if child.is_dir and child.expanded:
                    collect_visible(child)
        
        # Корень всегда развёрнут, собираем его детей
        if self.root.expanded:
            collect_visible(self.root)
        
        return result

    def get_selected_item(self) -> Optional[FileNode]:
        """Получить выбранный элемент"""
        visible = self.get_visible_items()
        if 0 <= self.selected_index < len(visible):
            return visible[self.selected_index]
        return None

    def move_up(self) -> None:
        """Переместить выделение вверх"""
        visible = self.get_visible_items()
        if visible:
            self.selected_index = max(0, self.selected_index - 1)

    def move_down(self) -> None:
        """Переместить выделение вниз"""
        visible = self.get_visible_items()
        if visible:
            self.selected_index = min(len(visible) - 1, self.selected_index + 1)

    def enter_directory(self) -> Optional[str]:
        """
        Войти в выбранную директорию или открыть файл
        
        Если выбрана директория - сделать её корнем дерева
        Если выбран файл - вернуть путь для открытия

        Returns:
            Путь к файлу для открытия, или None если директория
        """
        selected = self.get_selected_item()
        if not selected:
            return None

        if selected.is_dir:
            # Войти в директорию - сделать её корнем дерева
            self.current_path = selected.path
            self.selected_index = 0
            # Обновить корневой узел
            self.root = FileNode(name=os.path.basename(selected.path) or selected.path,
                                path=selected.path,
                                is_dir=True)
            self.root.expand()  # Корень всегда развёрнут
            return None
        else:
            # Открыть файл
            return selected.path

    def collapse_directory(self) -> None:
        """Свернуть выбранную директорию"""
        selected = self.get_selected_item()
        if selected and selected.is_dir:
            selected.collapse()

    def expand_directory(self) -> None:
        """Развернуть выбранную директорию"""
        selected = self.get_selected_item()
        if selected and selected.is_dir:
            selected.expand()

    def go_up_level(self) -> None:
        """Подняться на уровень выше"""
        parent_path = os.path.dirname(self.current_path)
        if parent_path != self.current_path:  # Если есть родительская директория
            self.current_path = parent_path
            self.selected_index = 0
            # Обновить корневой узел
            self.root = FileNode(name=os.path.basename(parent_path) or parent_path,
                                path=parent_path,
                                is_dir=True)
            self.root.expand()

    def delete_selected(self) -> bool:
        """
        ?Полный путьВыход? Выход/ВыходВыход??

        Returns:
            True Выход ??Полный путь???, False иначе
        """
        selected = self.get_selected_item()
        if not selected:
            return False

        try:
            if os.path.isdir(selected.path):
                # ??Полный путьВыход?? (Полный путь Выход??)
                os.rmdir(selected.path)
            else:
                # ??Полный путь?
                os.remove(selected.path)

            # ??Полный путь??
            if selected.parent:
                selected.parent.scanned = False
                selected.parent.scan_children()
            else:
                # Узел дерева файлов?? Выход???, ??Полный путь??
                self.root.scanned = False
                self.root.scan_children()

            # ВыходВыход???Узел дерева файлов???
            visible = self.get_visible_items()
            if self.selected_index >= len(visible):
                self.selected_index = max(0, len(visible) - 1)

            return True
        except (OSError, PermissionError):
            return False

    def refresh(self) -> None:
        """Обновить дерево (пересканировать текущую директорию)"""
        self.root.scanned = False
        self.root.scan_children()
        # Обновить развёрнутые директории
        def refresh_expanded(node: FileNode):
            for child in node.children:
                if child.expanded:
                    child.scanned = False
                    child.scan_children()
                    refresh_expanded(child)
        
        refresh_expanded(self.root)
    
    def reveal_path(self, file_path: str) -> bool:
        """
        Раскрыть дерево до указанного файла и установить на него выделение
        
        Args:
            file_path: Абсолютный путь к файлу
            
        Returns:
            True если файл найден и выделен, False иначе
        """
        # Нормализуем пути
        file_path = os.path.abspath(file_path)
        
        # Проверяем, что файл находится в текущем дереве
        if not file_path.startswith(self.current_path):
            return False
        
        # Получаем относительный путь от корня дерева
        relative_path = os.path.relpath(file_path, self.current_path)
        
        # Разбиваем путь на компоненты
        path_parts = relative_path.split(os.sep)
        
        # Раскрываем дерево по пути
        current_node = self.root
        
        for i, part in enumerate(path_parts[:-1]):  # Все кроме последнего (имени файла)
            # Сканируем детей если ещё не сканировали
            if not current_node.scanned:
                current_node.scan_children()
            
            # Ищем нужную директорию среди детей
            found = False
            for child in current_node.children:
                if child.name == part and child.is_dir:
                    # Раскрываем директорию
                    child.expand()
                    current_node = child
                    found = True
                    break
            
            if not found:
                return False
        
        # Сканируем последнюю директорию
        if not current_node.scanned:
            current_node.scan_children()
        
        # Ищем файл среди детей последней директории
        target_filename = path_parts[-1]
        visible_items = self.get_visible_items()
        
        for idx, item in enumerate(visible_items):
            if item.name == target_filename and item.path == file_path:
                # Нашли файл - устанавливаем выделение
                self.selected_index = idx
                return True
        
        return False