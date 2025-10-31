# -*- coding: utf-8 -*-
"""
Панель редактора (75% экрана)
"""

from seditor.terminal.layout import Layout


class EditorPane:
    """Панель редактора текста"""

    def __init__(self, layout: Layout):
        """
        Инициализация панели редактора

        Args:
            layout: Объект разметки экрана
        """
        self.layout = layout
        self.x, self.y, self.width, self.height = layout.get_editor_bounds()

    def render(self, terminal, focused: bool = False) -> str:
        """
        Отрендерить панель редактора

        Args:
            terminal: Объект blessed.Terminal
            focused: Активна ли панель (для подсветки фона)

        Returns:
            Строка с ANSI-кодами для отрисовки
        """
        output = []
        editor_x, editor_y, editor_width, editor_height = self.layout.get_editor_bounds()

        # Заголовок панели
        title = " Editor "
        if focused:
            # Неяркая подсветка фона для активной панели
            bg_color = terminal.on_color_rgb(40, 40, 40)  # Тёмно-серый
            output.append(terminal.move_xy(editor_x, editor_y) + bg_color + terminal.bold + title)
        else:
            output.append(terminal.move_xy(editor_x, editor_y) + terminal.bold + title)

        # Заполнение панели (временно - заглушка)
        for y in range(editor_y + 1, min(editor_y + editor_height, editor_y + 5)):
            if focused:
                bg_color = terminal.on_color_rgb(40, 40, 40)
                output.append(terminal.move_xy(editor_x, y) + bg_color + " " * editor_width)
            else:
                output.append(terminal.move_xy(editor_x, y) + " " * editor_width)

        # Временная заглушка
        placeholder = "Editor pane (75%)"
        mid_y = editor_y + editor_height // 2
        mid_x = editor_x + (editor_width - len(placeholder)) // 2
        output.append(terminal.move_xy(mid_x, mid_y) + placeholder)

        return "".join(output)
