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
        ????????????? ??? ???????? ??? ??????????? ? ????????? ? ????????? +/-

        Args:
            node: ???? ?Тёмно-серый
            max_width: ????Обновить дерево ??? ???????????

        Returns:
            ?????????Обновить дерево ? ?Тёмно-серый??
        """
        # Обновить дерево? ??????????? (???????)
        depth = node.get_depth()
        
        # ??????: 2 ??????? ?? ?Тёмно-серый? (??? ??????????)
        indent = "  " * depth
        
        # ?????? ??? ??????????: + ???? ????????, - ???? ??????????
        if node.is_dir:
            symbol = "-" if node.expanded else "+"
            prefix = f"{indent}{symbol} "
        else:
            prefix = f"{indent}  "  # ??? ?Тёмно-серый ??????
        
        name = prefix + node.name
        
        # ???????? ???? ??Тёмно-серый? ???
        if len(name) > max_width:
            name = name[:max_width - 3] + "..."
        
        return name

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
