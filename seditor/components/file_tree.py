# -*- coding: utf-8 -*-
"""
?Тёмно-серый ?????? (25% ??????)
"""

import os
from seditor.terminal.layout import Layout
from seditor.core.file_tree import FileTree, FileNode


class FileTreePane:
    """?????? ??Отрендерить панель дерева файлов"""

    def __init__(self, layout: Layout, root_path: str = None):
        """
        ????Отрендерить панель дерева файлов ??????

        Args:
            layout: ?????? Обновить дерево
            root_path: ???? ? Обновить дерево???? (?? ?Обновить дерево?)
        """
        self.layout = layout
        self.x, self.y, self.width, self.height = layout.get_tree_bounds()
        
        # ????Отрендерить панель дерева файлов
        if root_path is None:
            root_path = os.getcwd()
        self.tree = FileTree(root_path)
        
        # ???????? ??? ????????? (???? Отрендерить панель дерева файлов? ???????)
        self.scroll_offset = 0

    def get_display_height(self) -> int:
        """Обновить дерево ??Тёмно-серый????? (??? ?????????)"""
        return self.height - 1  # -1 ??? ?????????

    def _format_item_name(self, node: FileNode, max_width: int) -> str:
        """
        Форматирует имя элемента для отображения с отступами и иконками

        Args:
            node: Узел дерева файлов
            max_width: Максимальная ширина для отображения

        Returns:
            Отформатированная строка с иконкой
        """
        # Уровень вложенности (отступы)
        depth = node.get_depth()
        
        # Отступ: 2 пробела на уровень (для вложенности)
        indent = "  " * depth
        
        # Иконки для директорий и файлов
        if node.is_dir:
            # 📁 для свёрнутой папки, 📂 для развёрнутой
            icon = "🗂️" if node.expanded else "🗂️"
            prefix = f"{indent}{icon} "
        else:
            # Иконки для разных типов файлов
            icon = self._get_file_icon(node.name)
            prefix = f"{indent}{icon} "
        
        name = prefix + node.name
        
        # Обрезаем если слишком длинное имя
        if len(name) > max_width:
            name = name[:max_width - 3] + "..."
        
        return name
    
    def _get_file_icon(self, filename: str) -> str:
        """
        Получить иконку для файла на основе расширения
        
        Args:
            filename: Имя файла
            
        Returns:
            Unicode-символ иконки
        """
        import os
        ext = os.path.splitext(filename)[1].lower()
        
        # Маппинг расширений на иконки
        icon_map = {
            # Код
            '.py': '🐠',
            '.js': '🎊',
            '.ts': '🎊',
            '.jsx': '🎊',
            '.tsx': '🎊',
            '.java': '☕️',
            '.c': '©️',
            '.cpp': '©️',
            '.h': '©️',
            '.hpp': '©️',
            '.rs': '🦀',
            '.go': '🐹',
            '.rb': '💎',
            '.php': '🐘',
            '.swift': '🦅',
            '.kt': '🅺',
            
            # Веб
            '.html': '🌐',
            '.css': '🎨',
            '.scss': '🎨',
            '.sass': '🎨',
            '.less': '🎨',
            
            # Конфиги
            '.json': '⚙️',
            '.yaml': '⚙️',
            '.yml': '⚙️',
            '.toml': '⚙️',
            '.ini': '⚙️',
            '.conf': '⚙️',
            '.config': '⚙️',
            '.env': '🔐',
            
            # Документы
            '.md': '📖',
            '.txt': '📄',
            '.pdf': '📕',
            '.doc': '📘',
            '.docx': '📘',
            
            # Изображения
            '.png': '🖼️',
            '.jpg': '🖼️',
            '.jpeg': '🖼️',
            '.gif': '🖼️',
            '.svg': '🎨',
            '.ico': '🖼️',
            
            # Архивы
            '.zip': '📦',
            '.tar': '📦',
            '.gz': '📦',
            '.rar': '📦',
            '.7z': '📦',
            
            # Скрипты
            '.sh': '🉈',
            '.bash': '🉈',
            '.zsh': '🉈',
            '.fish': '🉈',
            
            # Данные
            '.sql': '🗄️',
            '.db': '🗄️',
            '.sqlite': '🗄️',
            '.csv': '📊',
            '.xml': '📋',
            
            # Специальные файлы
            '.lock': '🔒',
            '.log': '📜',
            '.gitignore': '🚫',
            '.dockerignore': '🚫',
        }
        
        # Специальные имена файлов
        special_names = {
            'Dockerfile': '🐳',
            'docker-compose.yml': '🐳',
            'Makefile': '🔨',
            'README.md': '📖',
            'LICENSE': '📜',
            'package.json': '📦',
            'requirements.txt': '📦',
            'Cargo.toml': '📦',
            'go.mod': '📦',
            'pyproject.toml': '📦',
            '.gitignore': '🚫',
            '.env': '🔐',
        }
        
        # Проверяем специальные имена
        if filename in special_names:
            return special_names[filename]
        
        # Проверяем расширение
        if ext in icon_map:
            return icon_map[ext]
        
        # По умолчанию - обычный файл
        return '📄'

    def render(self, terminal, focused: bool = False) -> str:
        """
        ??Отрендерить панель дерева файлов ??????

        Args:
            terminal: ?????? blessed.Terminal
            focused: ??????? ?? ?????? (??? ????????? ????)

        Returns:
            ?????? ? ANSI-?????? ??? ?????????
        """
        output = []
        tree_x, tree_y, tree_width, tree_height = self.layout.get_tree_bounds()

        # ?Обновить дерево
        title = " File Tree "
        if focused:
            # ??Тёмно-серый??? ???? ??? Обновить дерево
            bg_color = terminal.on_color_rgb(40, 40, 40)  # Тёмно-серый
            output.append(terminal.move_xy(tree_x, tree_y) + bg_color + terminal.bold + title)
        else:
            output.append(terminal.move_xy(tree_x, tree_y) + terminal.bold + title)

        # Обновить дерево? ????????
        visible_items = self.tree.get_visible_items()
        selected_item = self.tree.get_selected_item()

        # ?Обновить дерево???
        display_height = self.get_display_height()
        if self.tree.selected_index >= self.scroll_offset + display_height:
            self.scroll_offset = self.tree.selected_index - display_height + 1
        elif self.tree.selected_index < self.scroll_offset:
            self.scroll_offset = self.tree.selected_index

        # ??Обновить дерево??
        start_y = tree_y + 1
        max_items = min(len(visible_items), display_height)
        max_name_width = tree_width - 2  # -2 ??? ????????

        for i in range(max_items):
            item_index = self.scroll_offset + i
            if item_index >= len(visible_items):
                break

            item = visible_items[item_index]
            is_selected = (item == selected_item)
            y_pos = start_y + i

            # ?Форматируем имя для отображения с отступами и символами
            name = self._format_item_name(item, max_name_width)

            # ?Обновить дерево???? ????????
            if is_selected:
                if focused:
                    # ????? ?Обновить дерево???? ???????? ? Обновить дерево
                    bg_color = terminal.on_color_rgb(60, 60, 60)  # ?????
                    output.append(terminal.move_xy(tree_x + 1, y_pos) + bg_color + name)
                else:
                    # ????Обновить дерево??? ? ??Обновить дерево
                    bg_color = terminal.on_color_rgb(30, 30, 30)  # Тёмно-серый
                    output.append(terminal.move_xy(tree_x + 1, y_pos) + bg_color + name)
            else:
                # ??Тёмно-серый?
                if focused:
                    # ?Тёмно-серый?????? ??? ??? Обновить дерево
                    bg_color = terminal.on_color_rgb(40, 40, 40)  # Тёмно-серый
                    output.append(terminal.move_xy(tree_x + 1, y_pos) + bg_color + " " * tree_width)
                    output.append(terminal.move_xy(tree_x + 1, y_pos) + name)
                else:
                    output.append(terminal.move_xy(tree_x + 1, y_pos) + name)

            # ??????? ???Обновить дерево??????
            remaining_width = tree_width - len(name) - 1
            if remaining_width > 0:
                clear_line = " " * remaining_width
                output.append(terminal.move_xy(tree_x + 1 + len(name), y_pos) + clear_line)

        # ??Тёмно-серый???? ?????
        for i in range(max_items, display_height):
            y_pos = start_y + i
            clear_line = " " * tree_width
            if focused:
                bg_color = terminal.on_color_rgb(40, 40, 40)
                output.append(terminal.move_xy(tree_x, y_pos) + bg_color + clear_line)
            else:
                output.append(terminal.move_xy(tree_x, y_pos) + clear_line)

        return "".join(output)

    def _ensure_selection_visible(self, display_height: int, total_items: int) -> None:
        """??????????? ??????? ???????? ? ???????? ????????"""
        if display_height <= 0:
            self.scroll_offset = 0
            return
        if self.tree.selected_index >= self.scroll_offset + display_height:
            self.scroll_offset = self.tree.selected_index - display_height + 1
        elif self.tree.selected_index < self.scroll_offset:
            self.scroll_offset = self.tree.selected_index
        max_scroll = max(0, total_items - display_height)
        if self.scroll_offset > max_scroll:
            self.scroll_offset = max_scroll
        if self.scroll_offset < 0:
            self.scroll_offset = 0

    def get_display_lines(self, max_lines: int | None = None, max_width: int | None = None) -> list[tuple[str, bool]]:
        """???????? ?????? ??? ??????????? ?? prompt_toolkit"""
        visible_items = self.tree.get_visible_items()
        selected_item = self.tree.get_selected_item()

        display_height = max_lines if max_lines is not None else self.get_display_height()
        width_limit = max_width if max_width is not None else max(0, self.width - 2)

        self._ensure_selection_visible(display_height, len(visible_items))

        start_index = self.scroll_offset
        end_index = len(visible_items) if display_height is None else min(len(visible_items), start_index + display_height)

        lines: list[tuple[str, bool]] = []
        for idx in range(start_index, end_index):
            item = visible_items[idx]
            name = self._format_item_name(item, width_limit)
            lines.append((name, item == selected_item))

        return lines

    def move_up(self) -> None:
        """Переместить выделение вверх"""
        self.tree.move_up()

    def move_down(self) -> None:
        """Переместить выделение вниз"""
        self.tree.move_down()

    def enter(self) -> str | None:
        """
        Войти в директорию или открыть файл
        
        Если выбрана директория - сделать её корнем дерева
        Если выбран файл - открыть файл для редактирования

        Returns:
            Путь к файлу для открытия, или None если директория
        """
        return self.tree.enter_directory()

    def collapse_directory(self) -> None:
        """Свернуть выбранную директорию"""
        self.tree.collapse_directory()

    def expand_directory(self) -> None:
        """Развернуть выбранную директорию"""
        self.tree.expand_directory()

    def go_up_level(self) -> None:
        """Подняться на уровень выше"""
        self.tree.go_up_level()
        self.scroll_offset = 0  # Сброс прокрутки

    def delete_selected(self) -> bool:
        """
        Удалить выбранный файл/директорию

        Returns:
            True если удаление успешно, False иначе
        """
        return self.tree.delete_selected()

    def refresh(self) -> None:
        """Обновить дерево"""
        self.tree.refresh()
    
    def reveal_path(self, file_path: str) -> bool:
        """
        Раскрыть дерево до указанного файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если файл найден и выделен
        """
        return self.tree.reveal_path(file_path)
    
    def get_visible_items(self) -> list[FileNode]:
        """
        Получить список видимых элементов (с учётом прокрутки)
        
        Returns:
            Список видимых FileNode
        """
        all_items = self.tree.get_visible_items()
        
        if not all_items:
            return []
        
        # Применяем прокрутку
        start_index = self.scroll_offset
        end_index = min(start_index + self.height, len(all_items))
        
        return all_items[start_index:end_index]
