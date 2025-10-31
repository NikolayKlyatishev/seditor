# -*- coding: utf-8 -*-
"""
Управление терминалом - получение размеров, очистка, базовая работа с экраном
"""

from blessed import Terminal


class TerminalManager:
    """Менеджер терминала для управления экраном и базовыми операциями"""

    def __init__(self):
        """Инициализация терминала"""
        self.term = Terminal()
        self.width = self.term.width
        self.height = self.term.height

    def get_size(self) -> tuple[int, int]:
        """Получить размеры терминала (width, height)"""
        self.width = self.term.width
        self.height = self.term.height
        return self.width, self.height

    def clear(self) -> str:
        """Очистить экран"""
        return self.term.clear + self.term.home

    def move_cursor(self, x: int, y: int) -> str:
        """Переместить курсор в позицию (x, y)"""
        return self.term.move_xy(x, y)

    def hide_cursor(self) -> str:
        """Скрыть курсор"""
        return self.term.hide_cursor

    def show_cursor(self) -> str:
        """Показать курсор"""
        return self.term.show_cursor

    def enter_fullscreen(self) -> str:
        """Войти в полноэкранный режим"""
        return self.term.enter_fullscreen

    def exit_fullscreen(self) -> str:
        """Выйти из полноэкранного режима"""
        return self.term.exit_fullscreen

    def print_at(self, x: int, y: int, text: str) -> str:
        """Вывести текст в позиции (x, y)"""
        return self.move_cursor(x, y) + text

    def get_terminal(self) -> Terminal:
        """Получить объект терминала для расширенного использования"""
        return self.term

    def refresh_size(self) -> None:
        """Обновить размеры терминала"""
        self.width = self.term.width
        self.height = self.term.height

    def has_size_changed(self) -> bool:
        """
        Проверить, изменились ли размеры терминала

        Returns:
            True если размеры изменились, False иначе
        """
        new_width = self.term.width
        new_height = self.term.height
        if new_width != self.width or new_height != self.height:
            return True
        return False
