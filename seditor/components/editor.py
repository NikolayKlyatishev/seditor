# -*- coding: utf-8 -*-
"""
Панель редактора (75% экрана)
"""

import re
import logging
import subprocess
from typing import Optional
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.util import ClassNotFound
from pygments import lex
from pygments.token import Token
from seditor.terminal.layout import Layout
import pyperclip

logger = logging.getLogger(__name__)


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
        
        # Используем prompt_toolkit Buffer для управления текстом
        self.buffer = Buffer(
            name='editor',
            multiline=True,
            enable_history_search=False,
        )
        
        # Состояние редактора
        self.file_path: Optional[str] = None
        self.scroll_y = 0  # Вертикальная прокрутка
        self.scroll_x = 0  # Горизонтальная прокрутка
        
        # Ширина колонки номеров строк (по умолчанию 6 символов для номеров до 99999)
        self.line_number_width = 6
        
        # Лексер для подсветки синтаксиса
        self.lexer = None
        
        # Подсвеченные строки (храним подсвеченные версии строк для всего файла)
        self._highlighted_lines: list[str] = []
    
    def _update_lexer(self) -> None:
        """Обновить лексер для подсветки синтаксиса на основе расширения файла"""
        if self.file_path:
            try:
                # Пробуем определить лексер по имени файла
                self.lexer = get_lexer_for_filename(self.file_path, stripnl=False, ensurenl=False)
                logger.info(f"Lexer updated for {self.file_path}: {self.lexer.name}")
            except ClassNotFound:
                # Если не нашли лексер, используем текстовый
                try:
                    self.lexer = get_lexer_by_name('text', stripnl=False, ensurenl=False)
                    logger.info(f"Using text lexer for {self.file_path}")
                except ClassNotFound:
                    self.lexer = None
                    logger.warning(f"No lexer found for {self.file_path}")
            except Exception as e:
                logger.error(f"Error creating lexer for {self.file_path}: {e}", exc_info=True)
                self.lexer = None
        else:
            self.lexer = None
    
    def _highlight_line(self, line: str, terminal) -> str:
        """
        Подсветить синтаксис строки
        
        Args:
            line: Строка для подсветки
            terminal: Объект blessed.Terminal
            
        Returns:
            Строка с ANSI-кодами для подсветки синтаксиса
        """
        if not self.lexer or not terminal:
            return line
        
        try:
            # Получаем токены из строки
            tokens = list(lex(line, self.lexer))
            
            # Маппинг цветов Pygments на цвета blessed
            # Используем базовые цвета для различных типов токенов
            highlighted = ""
            for token_type, token_text in tokens:
                # Определяем цвет для типа токена
                color = self._get_token_color(token_type, terminal)
                if color:
                    highlighted += color + token_text + terminal.normal
                else:
                    highlighted += token_text
            
            return highlighted
        except Exception as e:
            logger.debug(f"Error highlighting line: {e}", exc_info=True)
            return line
    
    def _highlight_all_lines(self, terminal) -> None:
        """
        Подсветить все строки файла целиком
        
        Args:
            terminal: Объект blessed.Terminal для подсветки
        """
        # Очищаем старые подсвеченные строки
        self._highlighted_lines = []
        
        if not self.lexer or not terminal:
            # Если нет лексера, подсвеченные строки = оригинальные строки
            self._highlighted_lines = self.lines.copy()
            return
        
        # Подсвечиваем все строки целиком
        try:
            for line in self.lines:
                highlighted = self._highlight_line(line, terminal)
                self._highlighted_lines.append(highlighted)
            logger.info(f"Highlighted {len(self._highlighted_lines)} lines for file {self.file_path}")
        except Exception as e:
            logger.error(f"Error highlighting all lines: {e}", exc_info=True)
            # В случае ошибки используем оригинальные строки
            self._highlighted_lines = self.lines.copy()
    
    def _get_token_color(self, token_type, terminal):
        """
        Получить цвет для типа токена Pygments
        
        Args:
            token_type: Тип токена из Pygments
            terminal: Объект blessed.Terminal
            
        Returns:
            ANSI-код цвета или None
        """
        # Маппинг типов токенов на цвета
        # Используем цвета, которые хорошо видны на тёмном фоне
        
        # Проверяем типы токенов через строковое сравнение (более надежно)
        token_str = str(token_type)
        
        # Ключевые слова
        if 'Keyword' in token_str:
            return terminal.color_rgb(86, 156, 214)  # Синий
        
        # Строки
        elif 'String' in token_str:
            return terminal.color_rgb(206, 145, 120)  # Оранжево-коричневый
        
        # Числа
        elif 'Number' in token_str:
            return terminal.color_rgb(181, 206, 168)  # Зелёный
        
        # Комментарии
        elif 'Comment' in token_str:
            return terminal.color_rgb(106, 153, 85)  # Зелёный (темнее)
        
        # Имена (переменные, функции)
        elif 'Name' in token_str:
            # Функции - немного другой цвет
            if 'Function' in token_str:
                return terminal.color_rgb(220, 220, 170)  # Желтоватый
            elif 'Builtin' in token_str:
                return terminal.color_rgb(78, 201, 176)  # Зелёно-голубой
            elif 'Class' in token_str:
                return terminal.color_rgb(78, 201, 176)  # Зелёно-голубой
            else:
                return terminal.color_rgb(156, 220, 254)  # Светло-голубой
        
        # Операторы
        elif 'Operator' in token_str:
            return terminal.color_rgb(212, 212, 212)  # Светло-серый
        
        # Скобки
        elif 'Punctuation' in token_str:
            return terminal.color_rgb(212, 212, 212)  # Светло-серый
        
        # Остальное - обычный текст
        return None
    
    def _highlight_segment(self, segment: str, terminal, full_line: str, line_index: int, segment_start: int, segment_end: int) -> str:
        """
        Подсветить сегмент строки с учетом контекста
        
        Args:
            segment: Сегмент строки для подсветки (часть display_line)
            full_line: Полная строка (для контекста)
            line_index: Индекс строки
            segment_start: Начало сегмента в строке (относительно display_line, учитывая scroll_x)
            segment_end: Конец сегмента в строке
            terminal: Объект blessed.Terminal (обязателен для подсветки)
            
        Returns:
            Строка с ANSI-кодами для подсветки
        """
        if not self.lexer or not segment or not terminal:
            return segment
        
        try:
            # Подсвечиваем сегмент как часть полной строки
            # Для базовой подсветки подсвечиваем сегмент независимо
            # Это проще, но может быть менее точно для сложных конструкций
            
            tokens = list(lex(segment, self.lexer))
            
            highlighted = ""
            for token_type, token_text in tokens:
                color = self._get_token_color(token_type, terminal)
                if color:
                    highlighted += color + token_text + terminal.normal
                else:
                    highlighted += token_text
            
            return highlighted
        except Exception as e:
            logger.debug(f"Error highlighting segment: {e}", exc_info=True)
            return segment
    
    def _extract_segment_with_colors(self, highlighted_line: str, original_line: str, start: int, end: int, terminal) -> str:
        """
        Извлечь сегмент из подсвеченной строки с сохранением ANSI-кодов
        
        Args:
            highlighted_line: Подсвеченная строка (с ANSI-кодами)
            original_line: Оригинальная строка (без ANSI-кодов)
            start: Начало сегмента (индекс в оригинальной строке)
            end: Конец сегмента (индекс в оригинальной строке)
            terminal: Объект blessed.Terminal
            
        Returns:
            Сегмент с сохраненными ANSI-кодами
        """
        if start >= end or start >= len(original_line):
            return ""
        
        # Подсвечиваем сегмент отдельно (более простое решение)
        segment = original_line[start:end]
        if self.lexer and terminal:
            try:
                return self._highlight_segment(segment, terminal, original_line, 0, start, end)
            except:
                return segment
        return segment
    
    def _extract_char_with_colors(self, highlighted_line: str, original_line: str, pos: int) -> str:
        """
        Извлечь символ из подсвеченной строки с сохранением ANSI-кодов
        
        Args:
            highlighted_line: Подсвеченная строка (с ANSI-кодами)
            original_line: Оригинальная строка (без ANSI-кодов)
            pos: Позиция символа (индекс в оригинальной строке)
            
        Returns:
            Символ с сохраненными ANSI-кодами (или подсвеченный символ)
        """
        if pos >= len(original_line):
            return " "
        
        # Для символа под курсором возвращаем оригинальный символ
        # Подсветка будет применена через reverse курсора
        return original_line[pos]
    
    @property
    def lines(self) -> list[str]:
        """Получить список строк из буфера"""
        return self.buffer.text.split('\n') if self.buffer.text else ['']
    
    @property
    def cursor_y(self) -> int:
        """Получить вертикальную позицию курсора (номер строки)"""
        return self.buffer.document.cursor_position_row
    
    @property
    def cursor_x(self) -> int:
        """Получить горизонтальную позицию курсора (в символах)"""
        return self.buffer.document.cursor_position_col
        
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
            
            # Загружаем в буфер
            self.buffer.text = content
            self.file_path = file_path
            # Определяем лексер для подсветки синтаксиса
            self._update_lexer()
            self.buffer.cursor_position = 0
            self.scroll_y = 0
            self.scroll_x = 0
            return True
        except UnicodeDecodeError:
            # Файл не в UTF-8, пробуем другие кодировки
            for encoding in ['latin-1', 'cp1251', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    self.buffer.text = content
                    self.file_path = file_path
                    # Определяем лексер для подсветки синтаксиса
                    self._update_lexer()
                    self.buffer.cursor_position = 0
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
        self.buffer.cursor_up()
        self._adjust_scroll()

    def move_cursor_down(self) -> None:
        """Переместить курсор вниз"""
        self.buffer.cursor_down()
        self._adjust_scroll()

    def move_cursor_left(self) -> None:
        """Переместить курсор влево"""
        self.buffer.cursor_left()
        self._adjust_scroll()

    def move_cursor_right(self) -> None:
        """Переместить курсор вправо"""
        self.buffer.cursor_right()
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
        # Реализуем перемещение по словам вручную, так как Buffer не имеет встроенных методов
        current_line = self._get_current_line()
        
        if self.cursor_x > 0:
            # Ищем начало текущего или предыдущего слова
            word_start = self._find_word_start(current_line, self.cursor_x)
            # Перемещаем курсор на начало слова через установку позиции
            new_index = self.buffer.document.translate_row_col_to_index(self.cursor_y, word_start)
            self.buffer.cursor_position = new_index
            self._adjust_scroll()
        elif self.cursor_y > 0:
            # Переходим в конец предыдущей строки и ищем начало последнего слова
            self.buffer.cursor_up()
            prev_line = self._get_current_line()
            word_start = self._find_word_start(prev_line, len(prev_line))
            new_index = self.buffer.document.translate_row_col_to_index(self.cursor_y, word_start)
            self.buffer.cursor_position = new_index
            self._adjust_scroll()

    def move_cursor_word_right(self) -> None:
        """Переместить курсор в начало слова справа (Option+вправо)"""
        # Реализуем перемещение по словам вручную
        current_line = self._get_current_line()
        
        if self.cursor_x < len(current_line):
            # Ищем конец текущего или начало следующего слова
            word_end = self._find_word_end(current_line, self.cursor_x)
            # Перемещаем курсор на конец слова
            new_index = self.buffer.document.translate_row_col_to_index(self.cursor_y, word_end)
            self.buffer.cursor_position = new_index
            self._adjust_scroll()
        elif self.cursor_y < len(self.lines) - 1:
            # Переходим в начало следующей строки
            self.buffer.cursor_down()
            next_line = self._get_current_line()
            word_end = self._find_word_end(next_line, 0) if next_line else 0
            new_index = self.buffer.document.translate_row_col_to_index(self.cursor_y, word_end)
            self.buffer.cursor_position = new_index
            self._adjust_scroll()

    def insert_char(self, char: str) -> None:
        """Вставить символ в позицию курсора"""
        self.buffer.insert_text(char)
        self._adjust_scroll()

    def insert_newline(self) -> None:
        """Вставить новую строку (Enter)"""
        self.buffer.insert_text('\n')
        self._adjust_scroll()

    def delete_char_backward(self) -> None:
        """Удалить символ слева от курсора (Backspace)"""
        self.buffer.delete_before_cursor()
        self._adjust_scroll()

    def delete_char_forward(self) -> None:
        """Удалить символ справа от курсора (Delete)"""
        self.buffer.delete()
        self._adjust_scroll()

    def insert_tab(self, tab_size: int = 4) -> None:
        """Вставить табуляцию (Tab)"""
        spaces = " " * tab_size
        self.buffer.insert_text(spaces)
        self._adjust_scroll()
    
    def get_selected_text(self) -> str:
        """Получить выделенный текст через встроенные методы prompt_toolkit"""
        if self.buffer.selection_state and self.buffer.selection_state.has_selection():
            try:
                return self.buffer.copy_selection().text
            except (AttributeError, TypeError):
                pass
        return ""
    
    def get_selection_range(self) -> tuple[int, int] | None:
        """Получить диапазон выделения через встроенные методы prompt_toolkit"""
        if self.buffer.selection_state and self.buffer.selection_state.has_selection():
            try:
                start = self.buffer.selection_state.selection_start
                end = self.buffer.selection_state.selection_end
                return (start, end)
            except (AttributeError, TypeError):
                pass
        return None
    
    def copy_selected_text(self) -> bool:
        """
        Скопировать выделенный текст в буфер обмена
        
        Returns:
            True если текст был скопирован, False если нет выделения
        """
        selected_text = self.get_selected_text()
        logger.debug(f"copy_selected_text: selected_text length={len(selected_text) if selected_text else 0}, content={repr(selected_text[:50] if selected_text else '')}")
        
        if selected_text:
            try:
                # Пробуем через pyperclip
                pyperclip.copy(selected_text)
                # Проверяем, что текст действительно скопировался
                clipboard_check = pyperclip.paste()
                if clipboard_check == selected_text:
                    logger.info(f"Successfully copied {len(selected_text)} characters to clipboard via pyperclip")
                    return True
                else:
                    logger.warning(f"pyperclip copy failed, trying pbcopy...")
                    # Пробуем через системную команду pbcopy на macOS
                    try:
                        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
                        process.communicate(input=selected_text)
                        process.wait()
                        if process.returncode == 0:
                            logger.info(f"Successfully copied {len(selected_text)} characters to clipboard via pbcopy")
                            return True
                        else:
                            logger.error(f"pbcopy failed with return code {process.returncode}")
                            return False
                    except Exception as e2:
                        logger.error(f"Both pyperclip and pbcopy failed: {e}, {e2}", exc_info=True)
                        return False
            except Exception as e:
                logger.error(f"Failed to copy to clipboard: {e}", exc_info=True)
                # Пробуем через системную команду pbcopy на macOS
                try:
                    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
                    process.communicate(input=selected_text)
                    process.wait()
                    if process.returncode == 0:
                        logger.info(f"Successfully copied {len(selected_text)} characters to clipboard via pbcopy (fallback)")
                        return True
                except Exception as e2:
                    logger.error(f"Both pyperclip and pbcopy failed: {e}, {e2}", exc_info=True)
                return False
        else:
            logger.debug("No text selected for copy")
            return False
    
    def cut_selected_text(self) -> bool:
        """
        Вырезать выделенный текст (копировать и удалить)
        
        Returns:
            True если текст был вырезан, False если нет выделения
        """
        selected_text = self.get_selected_text()
        if selected_text:
            # Копируем в буфер обмена
            try:
                pyperclip.copy(selected_text)
                # Проверяем, что текст действительно скопировался
                clipboard_check = pyperclip.paste()
                if clipboard_check != selected_text:
                    # Пробуем через pbcopy
                    try:
                        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
                        process.communicate(input=selected_text)
                        process.wait()
                        if process.returncode == 0:
                            logger.info(f"Copied {len(selected_text)} characters to clipboard via pbcopy for cut")
                        else:
                            logger.error(f"pbcopy failed with return code {process.returncode}")
                            return False
                    except Exception as e2:
                        logger.error(f"Both pyperclip and pbcopy failed: {e2}", exc_info=True)
                        return False
                else:
                    logger.info(f"Copied {len(selected_text)} characters to clipboard for cut")
            except Exception as e:
                logger.error(f"Failed to copy to clipboard: {e}", exc_info=True)
                # Пробуем через pbcopy
                try:
                    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
                    process.communicate(input=selected_text)
                    process.wait()
                    if process.returncode == 0:
                        logger.info(f"Copied {len(selected_text)} characters to clipboard via pbcopy (fallback) for cut")
                    else:
                        return False
                except Exception as e2:
                    logger.error(f"Both pyperclip and pbcopy failed: {e}, {e2}", exc_info=True)
                    return False
            
            # Удаляем выделенный текст
            selection_range = self.get_selection_range()
            if selection_range:
                start_pos, end_pos = selection_range
                # Удаляем текст от start_pos до end_pos
                text_before = self.buffer.text[:start_pos]
                text_after = self.buffer.text[end_pos:]
                self.buffer.text = text_before + text_after
                # Перемещаем курсор на позицию start_pos
                self.buffer.cursor_position = start_pos
                # Выключаем режим выделения
                if self.buffer.selection_state is not None:
                    try:
                        self.buffer.selection_state.leave_shift_mode()
                    except (AttributeError, TypeError):
                        pass
                self._adjust_scroll()
                logger.info(f"Cut {len(selected_text)} characters")
                return True
        return False
    
    def paste_text(self) -> bool:
        """
        Вставить текст из буфера обмена
        
        Returns:
            True если текст был вставлен, False если буфер обмена пуст
        """
        try:
            # Пробуем через pyperclip
            clipboard_text = pyperclip.paste()
            # Если pyperclip не работает, пробуем через системную команду pbpaste на macOS
            if not clipboard_text:
                try:
                    result = subprocess.run(['pbpaste'], capture_output=True, text=True, timeout=1)
                    if result.returncode == 0:
                        clipboard_text = result.stdout
                        logger.debug(f"Got clipboard text via pbpaste: {len(clipboard_text)} chars")
                except Exception as e2:
                    logger.debug(f"pbpaste failed: {e2}")
            
            if clipboard_text:
                # Если есть выделение, заменяем его
                selected_text = self.get_selected_text()
                if selected_text:
                    selection_range = self.get_selection_range()
                    if selection_range:
                        start_pos, end_pos = selection_range
                        # Заменяем выделенный текст
                        text_before = self.buffer.text[:start_pos]
                        text_after = self.buffer.text[end_pos:]
                        self.buffer.text = text_before + clipboard_text + text_after
                        self.buffer.cursor_position = start_pos + len(clipboard_text)
                        # Выключаем режим выделения
                        if self.buffer.selection_state is not None:
                            try:
                                self.buffer.selection_state.leave_shift_mode()
                            except (AttributeError, TypeError):
                                pass
                        self._adjust_scroll()
                        logger.info(f"Pasted {len(clipboard_text)} characters (replaced selection)")
                        return True
                
                # Если выделения нет, просто вставляем в позицию курсора
                self.buffer.insert_text(clipboard_text)
                self._adjust_scroll()
                logger.info(f"Pasted {len(clipboard_text)} characters")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to paste from clipboard: {e}", exc_info=True)
            return False

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
            # Если курсор слева от видимой области - прокручиваем влево
            if self.cursor_x < self.scroll_x:
                self.scroll_x = self.cursor_x
            # Если курсор справа от видимой области - прокручиваем вправо
            # ВАЖНО: прокручиваем только когда курсор действительно за пределами видимой области
            # Не прокручиваем, если курсор просто в правой части видимой области
            elif self.cursor_x >= self.scroll_x + content_width:
                # Прокручиваем так, чтобы курсор был виден (в правом краю или немного левее)
                self.scroll_x = self.cursor_x - content_width + 1
                # Убеждаемся, что scroll_x не отрицательный
                if self.scroll_x < 0:
                    self.scroll_x = 0
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
            
        # Заголовок без фона
        output.append(terminal.move_xy(editor_x, editor_y) + terminal.bold + title)

        # Отображаем содержимое файла или заглушку
        if self.file_path and self.lines:
            # Проверяем, нужно ли подсвечивать весь файл (если еще не подсвечен)
            if len(self._highlighted_lines) != len(self.lines):
                self._highlight_all_lines(terminal)
            
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
                        # cursor_x - это позиция в оригинальной строке (без scroll_x)
                        # display_line начинается с позиции scroll_x, поэтому курсор в display_line = cursor_x - scroll_x
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
                
                # Отображаем номер строки (без фона)
                line_num_str = str(line_number).rjust(line_num_width - 1) + " "  # Выравнивание по правому краю + пробел
                separator_pos = line_number_start_x + line_num_width
                output.append(terminal.move_xy(line_number_start_x, y_pos) + terminal.color_rgb(100, 100, 100) + line_num_str + terminal.normal)
                output.append(terminal.move_xy(separator_pos, y_pos) + terminal.color_rgb(100, 100, 100) + "│" + terminal.normal)
                
                # Получаем диапазон выделения для этой строки
                selection_range = self.get_selection_range()
                selection_bg = terminal.on_color_rgb(60, 60, 120)  # Синеватый фон для выделения
                
                # Вычисляем границы выделения для текущей строки
                line_start_index = None
                line_end_index = None
                if selection_range:
                    start_char, end_char = selection_range
                    # Получаем индексы начала и конца текущей строки в тексте
                    try:
                        line_start_char = self.buffer.document.translate_row_col_to_index(i, 0)
                        # Индекс конца строки (начало следующей строки или конец текста)
                        # Важно: каждая строка заканчивается на символе '\n' (кроме последней)
                        if i + 1 < len(self.lines):
                            # Следующая строка существует - конец текущей строки это начало следующей (минус '\n')
                            line_end_char = self.buffer.document.translate_row_col_to_index(i + 1, 0) - 1
                        else:
                            # Последняя строка - конец это конец всего текста
                            line_end_char = len(self.buffer.text)
                        
                        # Проверяем пересечение выделения с текущей строкой
                        # Выделение пересекается, если start_char <= line_end_char И end_char > line_start_char
                        if start_char <= line_end_char + 1 and end_char > line_start_char:
                            # Выделение пересекается с этой строкой
                            # Начало выделения на этой строке (с учетом горизонтальной прокрутки)
                            if start_char >= line_start_char:
                                # Выделение начинается на этой строке - вычисляем относительную позицию
                                rel_start = start_char - line_start_char
                                line_start_index = max(0, rel_start - self.scroll_x)
                            else:
                                # Выделение начинается раньше (на предыдущих строках) - выделяем с начала строки
                                line_start_index = 0  # С начала строки (без учета scroll_x для начала строки)
                            
                            # Конец выделения на этой строке
                            if end_char <= line_end_char + 1:
                                # Выделение заканчивается на этой строке (включая '\n' если есть)
                                # end_char может быть на позиции после '\n', тогда выделяем до конца строки
                                if end_char > line_end_char:
                                    # end_char указывает на '\n' или после него - выделяем до конца строки
                                    line_end_index = len(display_line)
                                else:
                                    # end_char внутри строки - вычисляем относительную позицию
                                    rel_end = end_char - line_start_char
                                    line_end_index = min(len(display_line), rel_end - self.scroll_x)
                            else:
                                # Выделение продолжается на следующих строках - выделяем до конца строки
                                line_end_index = len(display_line)
                            
                            # Ограничиваем индексы диапазоном display_line и проверяем что start < end
                            line_start_index = max(0, min(line_start_index, len(display_line)))
                            line_end_index = max(line_start_index, min(line_end_index, len(display_line)))
                            
                            # Проверяем что выделение действительно видимо на этой строке
                            if line_start_index < line_end_index:
                                logger.debug(f"Line {i}: selection_range=({start_char}, {end_char}), line_range=({line_start_char}, {line_end_char}), display_range=({line_start_index}, {line_end_index}), line='{line[:30]}...'")
                            else:
                                # Выделение пустое для этой строки (может быть из-за scroll_x)
                                line_start_index = None
                                line_end_index = None
                    except (IndexError, AttributeError, ValueError) as e:
                        # Если возникла ошибка при вычислении, пропускаем выделение для этой строки
                        logger.debug(f"Error calculating selection for line {i}: {e}", exc_info=True)
                        line_start_index = None
                        line_end_index = None
                
                # Проверяем, нужно ли обновить подсвеченные строки
                # (если количество строк изменилось или подсветка не выполнялась)
                if len(self._highlighted_lines) != len(self.lines):
                    self._highlight_all_lines(terminal)
                
                # Используем уже подсвеченную строку для этой строки
                highlighted_line = self._highlighted_lines[i] if i < len(self._highlighted_lines) else line
                
                # Извлекаем видимую часть подсвеченной строки (с учетом scroll_x)
                if self.scroll_x > 0 and len(highlighted_line) > self.scroll_x:
                    # Нужно извлечь сегмент из подсвеченной строки
                    # Но ANSI-коды делают это сложным, поэтому используем простой подход:
                    # подсвечиваем display_line отдельно
                    highlighted_display = self._highlight_segment(display_line, terminal, line, i, self.scroll_x, self.scroll_x + len(display_line)) if self.lexer else display_line
                else:
                    # Берем подсвеченную строку целиком (или обрезаем до content_width)
                    highlighted_display = highlighted_line[:content_width] if len(highlighted_line) > content_width else highlighted_line
                    # Если строка обрезана, добавляем "..."
                    if len(line) > content_width:
                        highlighted_display = highlighted_display[:content_width - 3] + "..." if len(highlighted_display) > content_width - 3 else highlighted_display
                
                # Отображаем строку с курсором и выделением
                if focused and is_cursor_line and cursor_visible and 0 <= cursor_display_x_in_line < len(display_line):
                    # Если курсор на этой строке и в видимой области
                    # Без фона - используем подсвеченную строку целиком
                    line_output = terminal.move_xy(content_start_x, y_pos)
                    
                    # Простой подход: показываем подсвеченную строку, но выделение и курсор накладываем поверх
                    # ВАЖНО: cursor_display_x_in_line - это позиция в display_line (без ANSI-кодов)
                    # Но highlighted_display содержит ANSI-коды, поэтому позиции не совпадают
                    # Решение: используем оригинальную display_line для позиций, а подсвеченную для цветов
                    
                    # До выделения/курсора - подсвеченная часть
                    if line_start_index is not None and line_start_index > 0:
                        # Есть выделение до курсора
                        # Подсвечиваем часть до выделения отдельно
                        before_text = display_line[:line_start_index]
                        if self.lexer:
                            before_part = self._highlight_segment(before_text, terminal, line, i, self.scroll_x, self.scroll_x + line_start_index)
                        else:
                            before_part = before_text
                        line_output += before_part
                        
                        # Выделенный текст (без подсветки, только фон выделения)
                        selected_text = display_line[line_start_index:min(line_end_index, cursor_display_x_in_line)] if line_start_index < len(display_line) else ""
                        if selected_text:
                            line_output += selection_bg + selected_text + terminal.normal
                        
                        # Между выделением и курсором
                        if line_start_index < cursor_display_x_in_line:
                            between_text = display_line[line_start_index:cursor_display_x_in_line]
                            if self.lexer:
                                between_part = self._highlight_segment(between_text, terminal, line, i, self.scroll_x + line_start_index, self.scroll_x + cursor_display_x_in_line)
                            else:
                                between_part = between_text
                            line_output += between_part
                    elif cursor_display_x_in_line > 0:
                        # Нет выделения, просто до курсора
                        before_text = display_line[:cursor_display_x_in_line]
                        if self.lexer:
                            before_part = self._highlight_segment(before_text, terminal, line, i, self.scroll_x, self.scroll_x + cursor_display_x_in_line)
                        else:
                            before_part = before_text
                        line_output += before_part
                    else:
                        # Курсор в начале - ничего до него
                        pass
                    
                    # Курсор - используем оригинальный символ из display_line
                    if cursor_display_x_in_line < len(display_line):
                        char_under_cursor = display_line[cursor_display_x_in_line]
                        line_output += terminal.reverse + char_under_cursor + terminal.normal
                    
                    # После курсора
                    if cursor_display_x_in_line + 1 < len(display_line):
                        after_cursor_pos = cursor_display_x_in_line + 1
                        if line_end_index is not None and after_cursor_pos < line_end_index:
                            # Часть выделения после курсора
                            selected_after = display_line[after_cursor_pos:line_end_index]
                            if selected_after:
                                line_output += selection_bg + selected_after + terminal.normal
                            after_cursor_pos = line_end_index
                        
                        # Остаток строки с подсветкой
                        if after_cursor_pos < len(display_line):
                            after_text = display_line[after_cursor_pos:]
                            if self.lexer:
                                after_part = self._highlight_segment(after_text, terminal, line, i, self.scroll_x + after_cursor_pos, self.scroll_x + len(display_line))
                            else:
                                after_part = after_text
                            line_output += after_part
                    
                    output.append(line_output)
                    
                    # Очищаем оставшуюся часть строки (без фона)
                    remaining = content_width - len(display_line)
                    if remaining > 0:
                        output.append(" " * remaining)
                elif focused and is_cursor_line and cursor_display_x_in_line >= len(display_line):
                    # Курсор в конце строки (за пределами текста)
                    # Используем уже подсвеченную строку (без фона)
                    highlighted_display = self._highlight_segment(display_line, terminal, line, i, self.scroll_x, self.scroll_x + len(display_line)) if self.lexer else display_line
                    output.append(terminal.move_xy(content_start_x, y_pos) + highlighted_display)
                    # Отображаем курсор как пробел в конце (без фона)
                    cursor_pos = content_start_x + len(display_line)
                    if cursor_pos < content_start_x + content_width:
                        output.append(terminal.move_xy(cursor_pos, y_pos) + terminal.reverse + ' ' + terminal.normal)
                    # Очищаем оставшуюся часть (без фона)
                    remaining = content_width - len(display_line) - 1
                    if remaining > 0:
                        output.append(" " * remaining)
                else:
                    # Обычное отображение строки (без курсора или курсор вне видимой области)
                    # Проверяем выделение на этой строке
                    selection_range = self.get_selection_range()
                    selection_bg = terminal.on_color_rgb(60, 60, 120)  # Синеватый фон для выделения
                    
                    # Вычисляем границы выделения для текущей строки
                    line_start_index = None
                    line_end_index = None
                    if selection_range:
                        start_char, end_char = selection_range
                        try:
                            line_start_char = self.buffer.document.translate_row_col_to_index(i, 0)
                            # Индекс конца строки (начало следующей строки минус '\n' или конец текста)
                            if i + 1 < len(self.lines):
                                # Следующая строка существует - конец текущей строки это начало следующей (минус '\n')
                                line_end_char = self.buffer.document.translate_row_col_to_index(i + 1, 0) - 1
                            else:
                                # Последняя строка - конец это конец всего текста
                                line_end_char = len(self.buffer.text)
                            
                            # Проверяем пересечение выделения с текущей строкой
                            # Выделение пересекается, если start_char <= line_end_char + 1 И end_char > line_start_char
                            if start_char <= line_end_char + 1 and end_char > line_start_char:
                                # Выделение пересекается с этой строкой
                                # Начало выделения на этой строке (с учетом горизонтальной прокрутки)
                                if start_char >= line_start_char:
                                    # Выделение начинается на этой строке - вычисляем относительную позицию
                                    rel_start = start_char - line_start_char
                                    line_start_index = max(0, rel_start - self.scroll_x)
                                else:
                                    # Выделение начинается раньше (на предыдущих строках) - выделяем с начала строки
                                    line_start_index = 0  # С начала строки (без учета scroll_x для начала строки)
                                
                                # Конец выделения на этой строке
                                if end_char <= line_end_char + 1:
                                    # Выделение заканчивается на этой строке (включая '\n' если есть)
                                    # end_char может быть на позиции после '\n', тогда выделяем до конца строки
                                    if end_char > line_end_char:
                                        # end_char указывает на '\n' или после него - выделяем до конца строки
                                        line_end_index = len(display_line)
                                    else:
                                        # end_char внутри строки - вычисляем относительную позицию
                                        rel_end = end_char - line_start_char
                                        line_end_index = min(len(display_line), rel_end - self.scroll_x)
                                else:
                                    # Выделение продолжается на следующих строках - выделяем до конца строки
                                    line_end_index = len(display_line)
                                
                                # Ограничиваем индексы диапазоном display_line и проверяем что start < end
                                line_start_index = max(0, min(line_start_index, len(display_line)))
                                line_end_index = max(line_start_index, min(line_end_index, len(display_line)))
                                
                                # Проверяем что выделение действительно видимо на этой строке
                                if line_start_index >= line_end_index:
                                    # Выделение пустое для этой строки (может быть из-за scroll_x)
                                    line_start_index = None
                                    line_end_index = None
                        except (IndexError, AttributeError, ValueError) as e:
                            # Если возникла ошибка при вычислении, пропускаем выделение для этой строки
                            logger.debug(f"Error calculating selection for line {i}: {e}", exc_info=True)
                            line_start_index = None
                            line_end_index = None
                    
                    if line_start_index is not None:
                        # Есть выделение на этой строке
                        line_output = terminal.move_xy(content_start_x, y_pos)
                        
                        # Используем подсвеченную строку целиком
                        highlighted_display = self._highlight_segment(display_line, terminal, line, i, self.scroll_x, self.scroll_x + len(display_line)) if self.lexer else display_line
                        
                        # До выделения
                        if line_start_index > 0:
                            before_part = highlighted_display[:line_start_index] if line_start_index <= len(highlighted_display) else highlighted_display
                            line_output += before_part
                        
                        # Выделенный текст (без подсветки, только фон выделения)
                        if line_start_index < len(display_line):
                            selected_text = display_line[line_start_index:line_end_index]
                            line_output += selection_bg + selected_text + terminal.normal
                        
                        # После выделения
                        if line_end_index < len(display_line) and line_end_index < len(highlighted_display):
                            # Извлекаем остаток из подсвеченной строки
                            after_part = highlighted_display[line_end_index:]
                            line_output += after_part
                        elif line_end_index < len(display_line):
                            # Подсвечиваем остаток отдельно
                            after_text = display_line[line_end_index:]
                            if self.lexer:
                                after_part = self._highlight_segment(after_text, terminal, line, i, self.scroll_x + line_end_index, self.scroll_x + len(display_line))
                            else:
                                after_part = after_text
                            line_output += after_part
                        
                        output.append(line_output)
                    else:
                        # Нет выделения - обычное отображение с подсветкой синтаксиса
                        # Используем уже подсвеченную строку целиком
                        highlighted_display = self._highlight_segment(display_line, terminal, line, i, self.scroll_x, self.scroll_x + len(display_line)) if self.lexer else display_line
                        output.append(terminal.move_xy(content_start_x, y_pos) + highlighted_display)
                    
                    # Очищаем оставшуюся часть строки (без фона)
                    remaining = content_width - len(display_line)
                    if remaining > 0:
                        output.append(" " * remaining)
            
            # Очищаем оставшиеся строки (без фона)
            for y_pos in range(display_start + (end_line - start_line), display_start + display_height):
                # Отображаем пустую колонку номеров строк
                separator_pos = line_number_start_x + line_num_width
                output.append(terminal.move_xy(line_number_start_x, y_pos) + " " * line_num_width)
                output.append(terminal.move_xy(separator_pos, y_pos) + terminal.color_rgb(100, 100, 100) + "│" + terminal.normal)
                output.append(terminal.move_xy(content_start_x, y_pos) + " " * content_width)
            
        else:
            # Заглушка если файл не открыт (без фона)
            placeholder = "No file open. Press Enter on a file in the file tree to open it."
            mid_y = editor_y + editor_height // 2
            mid_x = editor_x + (editor_width - len(placeholder)) // 2
            output.append(terminal.move_xy(mid_x, mid_y) + placeholder)

        return "".join(output)
