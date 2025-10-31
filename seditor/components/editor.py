# -*- coding: utf-8 -*-
"""
Панель редактора (75% экрана)
"""

import re
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
        
        # Состояние редактора
        self.file_path: str | None = None
        self.lines: list[str] = []
        self.cursor_x = 0  # Горизонтальная позиция курсора (в символах)
        self.cursor_y = 0  # Вертикальная позиция курсора (номер строки)
        self.scroll_y = 0  # Вертикальная прокрутка
        self.scroll_x = 0  # Горизонтальная прокрутка
        
        # Ширина колонки номеров строк (по умолчанию 6 символов для номеров до 99999)
        self.line_number_width = 6
        
    def load_file(self, file_path: str) -> bool:
        """
        Загрузить файл в редактор
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если файл успешно загружен, False иначе
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разбиваем на строки, сохраняя окончания \n (но в списке без \n)
            self.lines = content.split('\n')
            
            # Если файл заканчивается на \n, добавляем пустую строку
            if content.endswith('\n'):
                self.lines.append('')
            
            self.file_path = file_path
            self.cursor_x = 0
            self.cursor_y = 0
            self.scroll_y = 0
            self.scroll_x = 0
            return True
        except UnicodeDecodeError:
            # Файл не в UTF-8, пробуем другие кодировки
            for encoding in ['latin-1', 'cp1251', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    self.lines = content.split('\n')
                    if content.endswith('\n'):
                        self.lines.append('')
                    self.file_path = file_path
                    self.cursor_x = 0
                    self.cursor_y = 0
                    self.scroll_y = 0
                    self.scroll_x = 0
                    return True
                except (UnicodeDecodeError, OSError):
                    continue
            return False
        except (OSError, PermissionError) as e:
            return False

    def get_display_height(self) -> int:
        """Получить высоту области отображения (без заголовка)"""
        return self.height - 1

    def _get_line_number_width(self) -> int:
        """Вычислить ширину колонки номеров строк"""
        if not self.lines:
            return self.line_number_width
        
        # Максимальный номер строки
        max_line_number = len(self.lines)
        # Ширина равна количеству цифр в максимальном номере + 1 символ пробела
        width = len(str(max_line_number)) + 1
        # Минимум 5 символов для читаемости
        return max(5, width)

    def _get_content_width(self, editor_width: int) -> int:
        """Получить ширину области содержимого (editor_width - колонка номеров - разделитель)"""
        line_num_width = self._get_line_number_width()
        separator_width = 1  # Разделитель между номерами и текстом
        return editor_width - line_num_width - separator_width

    def _get_current_line(self) -> str:
        """Получить текущую строку"""
        if 0 <= self.cursor_y < len(self.lines):
            return self.lines[self.cursor_y]
        return ""

    def _get_line_length(self, line_num: int) -> int:
        """Получить длину строки"""
        if 0 <= line_num < len(self.lines):
            return len(self.lines[line_num])
        return 0

    def move_cursor_up(self) -> None:
        """Переместить курсор вверх"""
        if self.cursor_y > 0:
            self.cursor_y -= 1
            # Ограничиваем курсор_x длиной новой строки
            max_x = self._get_line_length(self.cursor_y)
            if self.cursor_x > max_x:
                self.cursor_x = max_x
            self._adjust_scroll()

    def move_cursor_down(self) -> None:
        """Переместить курсор вниз"""
        if self.cursor_y < len(self.lines) - 1:
            self.cursor_y += 1
            # Ограничиваем курсор_x длиной новой строки
            max_x = self._get_line_length(self.cursor_y)
            if self.cursor_x > max_x:
                self.cursor_x = max_x
            self._adjust_scroll()

    def move_cursor_left(self) -> None:
        """Переместить курсор влево"""
        if self.cursor_x > 0:
            self.cursor_x -= 1
            self._adjust_scroll()
        elif self.cursor_y > 0:
            # Переходим в конец предыдущей строки
            self.cursor_y -= 1
            self.cursor_x = self._get_line_length(self.cursor_y)
            self._adjust_scroll()

    def move_cursor_right(self) -> None:
        """Переместить курсор вправо"""
        current_line_len = self._get_line_length(self.cursor_y)
        if self.cursor_x < current_line_len:
            self.cursor_x += 1
            self._adjust_scroll()
        elif self.cursor_y < len(self.lines) - 1:
            # Переходим в начало следующей строки
            self.cursor_y += 1
            self.cursor_x = 0
            self._adjust_scroll()

    def _find_word_start(self, line: str, pos: int) -> int:
        """Найти начало слова слева от позиции pos"""
        if pos == 0:
            return 0
        
        # Пропускаем текущий символ если он часть слова
        # Идём назад до начала слова или до пробела/разделителя
        i = pos - 1
        
        # Пропускаем пробелы/разделители справа от позиции
        while i >= 0 and not (line[i].isalnum() or line[i] == '_'):
            i -= 1
        
        # Если мы на символе слова, идём назад до начала слова
        if i >= 0 and (line[i].isalnum() or line[i] == '_'):
            while i > 0 and (line[i-1].isalnum() or line[i-1] == '_'):
                i -= 1
            return i
        
        # Если дошли до начала или нет слова, возвращаем позицию после пробелов
        return max(0, i + 1)

    def _find_word_end(self, line: str, pos: int) -> int:
        """Найти конец слова справа от позиции pos"""
        if pos >= len(line):
            return len(line)
        
        # Если текущий символ - пробел/разделитель, пропускаем их
        i = pos
        while i < len(line) and not (line[i].isalnum() or line[i] == '_'):
            i += 1
        
        # Если нашли символ слова, идём вперёд до конца слова
        if i < len(line) and (line[i].isalnum() or line[i] == '_'):
            while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                i += 1
            return i
        
        # Если нет слова, возвращаем позицию
        return i

    def move_cursor_word_left(self) -> None:
        """Переместить курсор в начало слова слева (Option+влево)"""
        current_line = self._get_current_line()
        
        if self.cursor_x > 0:
            # Ищем начало текущего или предыдущего слова
            word_start = self._find_word_start(current_line, self.cursor_x)
            self.cursor_x = word_start
            self._adjust_scroll()
        elif self.cursor_y > 0:
            # Переходим в конец предыдущей строки и ищем начало последнего слова
            self.cursor_y -= 1
            prev_line = self._get_current_line()
            self.cursor_x = self._find_word_start(prev_line, len(prev_line))
            self._adjust_scroll()

    def move_cursor_word_right(self) -> None:
        """Переместить курсор в начало слова справа (Option+вправо)"""
        current_line = self._get_current_line()
        
        if self.cursor_x < len(current_line):
            # Ищем конец текущего или начало следующего слова
            word_end = self._find_word_end(current_line, self.cursor_x)
            self.cursor_x = word_end
            self._adjust_scroll()
        elif self.cursor_y < len(self.lines) - 1:
            # Переходим в начало следующей строки
            self.cursor_y += 1
            next_line = self._get_current_line()
            self.cursor_x = self._find_word_start(next_line, 0) if next_line else 0
            self._adjust_scroll()

    def insert_char(self, char: str) -> None:
        """Вставить символ в позицию курсора"""
        if not self.lines:
            # Если файл пуст, создаём первую строку
            self.lines = [""]
            self.cursor_y = 0
        
        # Убеждаемся что курсор_y в допустимых пределах
        if self.cursor_y < 0:
            self.cursor_y = 0
        elif self.cursor_y >= len(self.lines):
            # Добавляем новые пустые строки если нужно
            while len(self.lines) <= self.cursor_y:
                self.lines.append("")
        
        current_line = self.lines[self.cursor_y]
        
        # Убеждаемся что курсор_x в допустимых пределах
        if self.cursor_x < 0:
            self.cursor_x = 0
        elif self.cursor_x > len(current_line):
            self.cursor_x = len(current_line)
        
        # Вставляем символ
        self.lines[self.cursor_y] = current_line[:self.cursor_x] + char + current_line[self.cursor_x:]
        # Перемещаем курсор вправо
        self.cursor_x += 1
        self._adjust_scroll()

    def insert_newline(self) -> None:
        """Вставить новую строку (Enter)"""
        if not self.lines:
            # Если файл пуст, создаём две строки
            self.lines = ["", ""]
            self.cursor_y = 0
            self.cursor_x = 0
            return
        
        # Убеждаемся что курсор_y в допустимых пределах
        if self.cursor_y < 0:
            self.cursor_y = 0
        elif self.cursor_y >= len(self.lines):
            # Добавляем новые пустые строки если нужно
            while len(self.lines) <= self.cursor_y:
                self.lines.append("")
        
        current_line = self.lines[self.cursor_y]
        
        # Убеждаемся что курсор_x в допустимых пределах
        if self.cursor_x < 0:
            self.cursor_x = 0
        elif self.cursor_x > len(current_line):
            self.cursor_x = len(current_line)
        
        # Разбиваем строку на две части
        before_cursor = current_line[:self.cursor_x]
        after_cursor = current_line[self.cursor_x:]
        
        # Обновляем текущую строку (часть до курсора)
        self.lines[self.cursor_y] = before_cursor
        # Вставляем новую строку (часть после курсора)
        self.lines.insert(self.cursor_y + 1, after_cursor)
        # Перемещаем курсор на новую строку в начало
        self.cursor_y += 1
        self.cursor_x = 0
        self._adjust_scroll()

    def delete_char_backward(self) -> None:
        """Удалить символ слева от курсора (Backspace)"""
        if not self.lines:
            return
        
        # Убеждаемся что курсор_y в допустимых пределах
        if self.cursor_y < 0 or self.cursor_y >= len(self.lines):
            return
        
        current_line = self.lines[self.cursor_y]
        
        if self.cursor_x > 0:
            # Удаляем символ слева от курсора
            self.lines[self.cursor_y] = current_line[:self.cursor_x - 1] + current_line[self.cursor_x:]
            self.cursor_x -= 1
            self._adjust_scroll()
        elif self.cursor_y > 0:
            # Объединяем с предыдущей строкой
            prev_line = self.lines[self.cursor_y - 1]
            prev_line_length = len(prev_line)
            self.lines[self.cursor_y - 1] = prev_line + current_line
            self.lines.pop(self.cursor_y)
            self.cursor_y -= 1
            self.cursor_x = prev_line_length
            self._adjust_scroll()

    def delete_char_forward(self) -> None:
        """Удалить символ справа от курсора (Delete)"""
        if not self.lines:
            return
        
        # Убеждаемся что курсор_y в допустимых пределах
        if self.cursor_y < 0 or self.cursor_y >= len(self.lines):
            return
        
        current_line = self.lines[self.cursor_y]
        
        if self.cursor_x < len(current_line):
            # Удаляем символ справа от курсора
            self.lines[self.cursor_y] = current_line[:self.cursor_x] + current_line[self.cursor_x + 1:]
            self._adjust_scroll()
        elif self.cursor_y < len(self.lines) - 1:
            # Объединяем со следующей строкой
            next_line = self.lines[self.cursor_y + 1]
            self.lines[self.cursor_y] = current_line + next_line
            self.lines.pop(self.cursor_y + 1)
            self._adjust_scroll()

    def insert_tab(self, tab_size: int = 4) -> None:
        """Вставить табуляцию (Tab)"""
        # Вставляем пробелы вместо табуляции
        if not self.lines:
            # Если файл пуст, создаём первую строку
            self.lines = [""]
            self.cursor_y = 0
        
        # Убеждаемся что курсор_y в допустимых пределах
        if self.cursor_y < 0:
            self.cursor_y = 0
        elif self.cursor_y >= len(self.lines):
            # Добавляем новые пустые строки если нужно
            while len(self.lines) <= self.cursor_y:
                self.lines.append("")
        
        current_line = self.lines[self.cursor_y]
        
        # Убеждаемся что курсор_x в допустимых пределах
        if self.cursor_x < 0:
            self.cursor_x = 0
        elif self.cursor_x > len(current_line):
            self.cursor_x = len(current_line)
        
        # Вставляем пробелы
        spaces = " " * tab_size
        self.lines[self.cursor_y] = current_line[:self.cursor_x] + spaces + current_line[self.cursor_x:]
        # Перемещаем курсор вправо на количество пробелов
        self.cursor_x += tab_size
        self._adjust_scroll()

    def _adjust_scroll(self) -> None:
        """Подстроить прокрутку так, чтобы курсор был виден"""
        editor_x, editor_y, editor_width, editor_height = self.layout.get_editor_bounds()
        display_height = editor_height - 1
        display_start = editor_y + 1
        content_width = self._get_content_width(editor_width)

        # Вертикальная прокрутка
        # Если курсор выше видимой области
        if self.cursor_y < self.scroll_y:
            self.scroll_y = self.cursor_y
        # Если курсор ниже видимой области
        elif self.cursor_y >= self.scroll_y + display_height:
            self.scroll_y = self.cursor_y - display_height + 1

        # Горизонтальная прокрутка (если строка длиннее ширины содержимого)
        current_line = self._get_current_line()
        if len(current_line) > content_width:
            # Если курсор слева от видимой области
            if self.cursor_x < self.scroll_x:
                self.scroll_x = self.cursor_x
            # Если курсор справа от видимой области
            elif self.cursor_x >= self.scroll_x + content_width:
                self.scroll_x = self.cursor_x - content_width + 1
        else:
            # Если строка помещается, сбрасываем горизонтальную прокрутку
            self.scroll_x = 0

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
        display_height = editor_height - 1
        display_start = editor_y + 1
        
        # Вычисляем ширину колонки номеров строк и доступную ширину для содержимого
        line_num_width = self._get_line_number_width()
        content_width = self._get_content_width(editor_width)
        line_number_start_x = editor_x
        content_start_x = editor_x + line_num_width + 1  # +1 для разделителя

        # Заголовок панели с именем файла
        if self.file_path:
            import os
            filename = os.path.basename(self.file_path)
            title = f" Editor: {filename} "
        else:
            title = " Editor "
            
        if focused:
            # Неяркая подсветка фона для активной панели
            bg_color = terminal.on_color_rgb(40, 40, 40)  # Тёмно-серый
            output.append(terminal.move_xy(editor_x, editor_y) + bg_color + terminal.bold + title)
        else:
            output.append(terminal.move_xy(editor_x, editor_y) + terminal.bold + title)

        # Отображаем содержимое файла или заглушку
        if self.file_path and self.lines:
            # Подстраиваем прокрутку перед отрисовкой
            self._adjust_scroll()
            
            # Ограничиваем прокрутку
            max_scroll = max(0, len(self.lines) - display_height)
            if self.scroll_y > max_scroll:
                self.scroll_y = max_scroll
            if self.scroll_y < 0:
                self.scroll_y = 0

            # Определяем строки для отображения
            start_line = self.scroll_y
            end_line = min(start_line + display_height, len(self.lines))
            
            # Отображаем строки файла
            for i in range(start_line, end_line):
                line = self.lines[i]
                y_pos = display_start + (i - start_line)
                is_cursor_line = (i == self.cursor_y)
                line_number = i + 1  # Номер строки (начинается с 1)
                
                # Применяем горизонтальную прокрутку
                if len(line) > self.scroll_x:
                    display_line = line[self.scroll_x:]
                    # Вычисляем видимую позицию курсора в строке (если это строка с курсором)
                    if is_cursor_line:
                        cursor_display_x_in_line = self.cursor_x - self.scroll_x
                    else:
                        cursor_display_x_in_line = -1
                else:
                    display_line = ""
                    cursor_display_x_in_line = -1 if not is_cursor_line else 0
                
                # Обрезаем строку если она слишком длинная (но помним позицию курсора)
                cursor_visible = (0 <= cursor_display_x_in_line < len(display_line)) if is_cursor_line else False
                if len(display_line) > content_width:
                    # Если курсор видимый, проверяем что он не обрезан
                    if cursor_visible and cursor_display_x_in_line >= content_width - 3:
                        # Курсор будет обрезан, но мы его всё равно отобразим
                        display_line = display_line[:content_width - 3] + "..."
                        cursor_visible = False  # Курсор за пределами обрезанной строки
                    elif cursor_visible:
                        # Курсор в видимой области до обрезания
                        display_line = display_line[:content_width - 3] + "..."
                    else:
                        display_line = display_line[:content_width - 3] + "..."
                
                # Отображаем номер строки
                line_num_str = str(line_number).rjust(line_num_width - 1) + " "  # Выравнивание по правому краю + пробел
                if focused:
                    bg_color = terminal.on_color_rgb(40, 40, 40)
                    # Номера строк на сером фоне, но менее ярком
                    line_num_bg = terminal.on_color_rgb(30, 30, 30)  # Ещё более тёмный для номеров
                    # Отображаем номер строки и разделитель вместе
                    separator_pos = line_number_start_x + line_num_width
                    output.append(terminal.move_xy(line_number_start_x, y_pos) + line_num_bg + terminal.color_rgb(150, 150, 150) + line_num_str + terminal.normal)
                    output.append(terminal.move_xy(separator_pos, y_pos) + bg_color + "│" + terminal.normal)
                else:
                    # Номера строк без фона, приглушённым цветом
                    separator_pos = line_number_start_x + line_num_width
                    output.append(terminal.move_xy(line_number_start_x, y_pos) + terminal.color_rgb(100, 100, 100) + line_num_str + terminal.normal)
                    output.append(terminal.move_xy(separator_pos, y_pos) + "│")
                
                # Отображаем строку с курсором если нужно
                if focused and is_cursor_line and cursor_visible and 0 <= cursor_display_x_in_line < len(display_line):
                    # Если курсор на этой строке и в видимой области
                    bg_color = terminal.on_color_rgb(40, 40, 40)
                    
                    # Отображаем часть строки до курсора
                    before_cursor = display_line[:cursor_display_x_in_line]
                    output.append(terminal.move_xy(content_start_x, y_pos) + bg_color + before_cursor)
                    
                    # Отображаем символ под курсором (inverse video)
                    char_under_cursor = display_line[cursor_display_x_in_line]
                    output.append(terminal.reverse + char_under_cursor + terminal.normal + bg_color)
                    
                    # Отображаем часть строки после курсора
                    after_cursor = display_line[cursor_display_x_in_line + 1:]
                    output.append(after_cursor)
                    
                    # Очищаем оставшуюся часть строки
                    remaining = content_width - len(display_line)
                    if remaining > 0:
                        output.append(bg_color + " " * remaining + terminal.normal)
                elif focused and is_cursor_line and cursor_display_x_in_line >= len(display_line):
                    # Курсор в конце строки (за пределами текста)
                    bg_color = terminal.on_color_rgb(40, 40, 40)
                    output.append(terminal.move_xy(content_start_x, y_pos) + bg_color + display_line)
                    # Отображаем курсор как пробел в конце
                    cursor_pos = content_start_x + len(display_line)
                    if cursor_pos < content_start_x + content_width:
                        output.append(terminal.move_xy(cursor_pos, y_pos) + terminal.reverse + ' ' + terminal.normal + bg_color)
                    # Очищаем оставшуюся часть
                    remaining = content_width - len(display_line) - 1
                    if remaining > 0:
                        output.append(bg_color + " " * remaining + terminal.normal)
                else:
                    # Обычное отображение строки
                    if focused:
                        bg_color = terminal.on_color_rgb(40, 40, 40)
                        output.append(terminal.move_xy(content_start_x, y_pos) + bg_color + display_line)
                        # Очищаем оставшуюся часть строки
                        remaining = content_width - len(display_line)
                        if remaining > 0:
                            output.append(bg_color + " " * remaining + terminal.normal)
                    else:
                        output.append(terminal.move_xy(content_start_x, y_pos) + display_line)
                        # Очищаем оставшуюся часть строки
                        remaining = content_width - len(display_line)
                        if remaining > 0:
                            output.append(" " * remaining)
            
            # Очищаем оставшиеся строки
            for y_pos in range(display_start + (end_line - start_line), display_start + display_height):
                # Отображаем пустую колонку номеров строк
                separator_pos = line_number_start_x + line_num_width
                if focused:
                    line_num_bg = terminal.on_color_rgb(30, 30, 30)
                    bg_color = terminal.on_color_rgb(40, 40, 40)
                    output.append(terminal.move_xy(line_number_start_x, y_pos) + line_num_bg + " " * line_num_width + terminal.normal)
                    output.append(terminal.move_xy(separator_pos, y_pos) + bg_color + "│" + terminal.normal)
                    output.append(terminal.move_xy(content_start_x, y_pos) + bg_color + " " * content_width + terminal.normal)
                else:
                    output.append(terminal.move_xy(line_number_start_x, y_pos) + " " * line_num_width)
                    output.append(terminal.move_xy(separator_pos, y_pos) + "│")
                    output.append(terminal.move_xy(content_start_x, y_pos) + " " * content_width)
            
        else:
            # Заглушка если файл не открыт
            placeholder = "No file open. Press Enter on a file in the file tree to open it."
            if not focused:
                mid_y = editor_y + editor_height // 2
                mid_x = editor_x + (editor_width - len(placeholder)) // 2
                output.append(terminal.move_xy(mid_x, mid_y) + placeholder)
            else:
                # Если панель активна, заполняем фон
                for y_pos in range(display_start, display_start + display_height):
                    bg_color = terminal.on_color_rgb(40, 40, 40)
                    output.append(terminal.move_xy(editor_x, y_pos) + bg_color + " " * editor_width + terminal.normal)

        return "".join(output)
