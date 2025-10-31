# -*- coding: utf-8 -*-
"""
Основной класс приложения
"""

import logging
from seditor.terminal.manager import TerminalManager
from seditor.terminal.layout import Layout
from seditor.components.file_tree import FileTreePane
from seditor.components.editor import EditorPane

# Настройка логирования для отладки
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='seditor_debug.log'
)
logger = logging.getLogger(__name__)


class App:
    """Главный класс приложения seditor"""

    def __init__(self):
        """Инициализация приложения"""
        self.term_manager = TerminalManager()
        width, height = self.term_manager.get_size()
        self.layout = Layout(width, height)
        self.file_tree = FileTreePane(self.layout)
        self.editor = EditorPane(self.layout)
        self.running = False
        
        # Система фокуса: 'tree' | 'editor' | 'command'
        self.focused_pane = 'tree'  # По умолчанию фокус на дереве
        
        # Путь к текущему открытому файлу
        self.current_file = None
        
        # Включить отладку клавиш (выводить в консоль)
        self.debug_keys = True
        
        # Для отслеживания Option+стрелок через быстрое повторение стрелок
        # Если стрелки влево/вправо нажимаются быстро подряд - это перемещение по словам
        import time
        self._last_arrow_key = None  # Последняя нажатая стрелка ('KEY_LEFT' или 'KEY_RIGHT')
        self._last_arrow_time = 0    # Время последней стрелки
        
        # Для отслеживания Shift+Up/Down через состояние выделения
        # Отслеживаем последнее нажатие Shift+Right/Left, чтобы понять,
        # что следующие Up/Down могут быть Shift+Up/Down
        self._last_shift_arrow_time = 0  # Время последнего Shift+Right/Left
        self._shift_arrow_timeout = 0.5  # Таймаут для продолжения выделения после Shift+Right/Left (500ms)
        

    def _draw_separator(self, terminal) -> str:
        """
        Нарисовать вертикальный разделитель между панелями

        Args:
            terminal: Объект blessed.Terminal

        Returns:
            Строка с ANSI-кодами для отрисовки разделителя
        """
        output = []
        separator_x = self.layout.separator_x
        height = self.layout.height

        # Вертикальная линия разделителя
        for y in range(height):
            output.append(terminal.move_xy(separator_x, y) + "│")

        return "".join(output)

    def _render_all(self) -> str:
        """
        Отрендерить весь экран (обе панели + разделитель)

        Returns:
            Строка с ANSI-кодами для полной отрисовки
        """
        terminal = self.term_manager.get_terminal()
        output = []

        # Очистка экрана
        output.append(self.term_manager.clear())

        # Отрисовка панели дерева файлов (с фокусом)
        output.append(self.file_tree.render(terminal, focused=(self.focused_pane == 'tree')))

        # Отрисовка разделителя
        output.append(self._draw_separator(terminal))

        # Отрисовка панели редактора (с фокусом)
        output.append(self.editor.render(terminal, focused=(self.focused_pane == 'editor')))

        return "".join(output)

    def _render_with_status(self) -> None:
        """Отрендерить экран и статусную строку"""
        terminal = self.term_manager.get_terminal()
        output = self._render_all()
        
        # Статусная строка
        focus_indicator = f"[{self.focused_pane.upper()}]" if self.focused_pane else ""
        status_msg = f"Press 'q' to quit | Tab to switch | {focus_indicator}"
        status_y = self.layout.height - 1
        status_x = 0
        # Очистить строку перед выводом статуса
        status_line = terminal.move_xy(status_x, status_y) + " " * self.layout.terminal_width
        status_text = terminal.move_xy(status_x, status_y) + status_msg
        
        print(output + status_line + status_text, end="", flush=True)

    def _toggle_focus(self) -> None:
        """Переключить фокус между панелями (Command+Tab или Tab)"""
        if self.focused_pane == 'tree':
            self.focused_pane = 'editor'
        elif self.focused_pane == 'editor':
            self.focused_pane = 'tree'
        # command пока не реализована

    def _log_key(self, inp, context: str = "") -> None:
        """Логировать информацию о нажатой клавише для отладки"""
        if self.debug_keys:
            key_info = {
                'repr': repr(inp),
                'str': str(inp),
                'name': getattr(inp, 'name', 'NO_NAME'),
                'code': getattr(inp, 'code', 'NO_CODE'),
                'is_sequence': getattr(inp, 'is_sequence', 'NO_IS_SEQUENCE'),
            }
            logger.debug(f"Key pressed {context}: {key_info}")
            # Также выводим в файл для отладки
            with open('seditor_keys.log', 'a') as f:
                f.write(f"{context}: {key_info}\n")

    def _handle_tree_key(self, inp) -> None:
        """Обработать клавишу в панели дерева файлов"""
        # # Логирование для отладки
        self._log_key(inp, f"[TREE FOCUS]")
        
        # # В blessed для специальных клавиш нужно проверять .name или .is_sequence
        key_name = getattr(inp, 'name', None)
        key_code = getattr(inp, 'code', None)
        key_str = str(inp)
        
        logger.debug(f"Processing key: name={key_name}, code={key_code}, str={key_str}")
        
        # ??Очистка экрана???
        if key_name == 'KEY_UP' or (key_code and 'up' in str(key_code).lower()):
            logger.debug("Moving UP")
            self.file_tree.move_up()
        elif key_name == 'KEY_DOWN' or (key_code and 'down' in str(key_code).lower()):
            logger.debug("Moving DOWN")
            self.file_tree.move_down()
        elif key_str == '\x1b[A':  # ESC[A - стрелка вверх
            logger.debug("Moving UP (ESC sequence)")
            self.file_tree.move_up()
        elif key_str == '\x1b[B':  # ESC[B - стрелка вниз
            logger.debug("Moving DOWN (ESC sequence)")
            self.file_tree.move_down()
        
        # Enter - войти в директорию или открыть файл
        elif key_name == 'KEY_ENTER' or key_str == '\n' or key_str == '\r':
            logger.debug("Enter pressed")
            try:
                result = self.file_tree.enter()
                logger.debug(f"Enter result: {result}")
                if result:
                    # Открыть файл в редакторе
                    self.current_file = result
                    # Загрузить файл в редактор
                    if self.editor.load_file(result):
                        logger.debug(f"File loaded: {result}")
                        self.focused_pane = 'editor'  # Переключить фокус на редактор
                    else:
                        logger.error(f"Failed to load file: {result}")
                # Если result is None - это директория, она уже установлена как корень
            except Exception as e:
                logger.error(f"Ошибка при обработке Enter: {e}", exc_info=True)
        
        # Стрелки для сворачивания/разворачивания
        elif key_name == 'KEY_LEFT' or key_str == '\x1b[D':  # ESC[D
            logger.debug("Left arrow - collapsing")
            self.file_tree.collapse_directory()
        elif key_name == 'KEY_RIGHT' or key_str == '\x1b[C':  # ESC[C
            logger.debug("Right arrow - expanding")
            self.file_tree.expand_directory()
        
        # Backspace - Backspace - подняться на уровень выше
        elif key_name == 'KEY_BACKSPACE' or key_str == '\x7f' or key_str == '\b':
            logger.debug("Backspace - going up level")
            self.file_tree.go_up_level()
        
        # Command+Backspace - Выход??? Выход (? ВременноВыход)
        # TODO: ???Очистка экранаВыход Command+Backspace ?? macOS

    def _handle_editor_key(self, inp) -> None:
        """Обработать клавишу в панели редактора"""
        # Логирование для отладки
        self._log_key(inp, f"[EDITOR FOCUS]")
        
        # Получаем информацию о клавише
        key_name = getattr(inp, 'name', None)
        key_code = getattr(inp, 'code', None)
        key_str = str(inp)
        is_sequence = getattr(inp, 'is_sequence', False)
        
        # Расширенное логирование для отладки Option+стрелок и Command+C/X/V
        # Логируем все клавиши для отладки Command+C/X/V
        if key_code in (3, 24, 22) or key_str in ('\x03', '\x18', '\x16'):
            logger.info(f"Potential Command key: name={key_name}, code={key_code}, str={repr(key_str)}, is_sequence={is_sequence}")
        logger.debug(f"Editor key: name={key_name}, code={key_code}, str={repr(key_str)}, is_sequence={is_sequence}")
        
        # Проверяем Option+стрелки для перемещения по словам (macOS) - проверяем ПЕРВЫМИ
        # На macOS Option+стрелка отправляет ESC-последовательность с модификатором
        # Возможные варианты:
        # \x1b[1;3D - Option+влево (Meta+влево)
        # \x1b[1;3C - Option+вправо (Meta+вправо)
        # \x1b[1;5D - Ctrl+влево
        # \x1b[1;5C - Ctrl+вправо
        # \x1b[1;9D - Shift+Option+влево
        # \x1b[1;9C - Shift+Option+вправо
        # \x1bOD - вариант Option+влево в некоторых терминалах
        # \x1bOC - вариант Option+вправо в некоторых терминалах
        
        # Получаем байтовое представление для более точной проверки
        try:
            key_bytes = key_str.encode('latin-1') if isinstance(key_str, str) else bytes(key_str)
        except:
            key_bytes = b''
        
        # Проверяем различные варианты Option+влево
        option_left_patterns = [
            b'\x1b[1;3D',  # Стандартный вариант
            b'\x1b[1;5D',  # Ctrl+влево (тоже используем)
            b'\x1b[1;9D',  # Shift+Option+влево
            b'\x1bOD',     # Альтернативный вариант
            '\x1b[1;3D',   # Строковый вариант
            '\x1b[1;5D',
            '\x1b[1;9D',
            '\x1bOD',
        ]
        
        # Проверяем различные варианты Option+вправо
        option_right_patterns = [
            b'\x1b[1;3C',  # Стандартный вариант
            b'\x1b[1;5C',  # Ctrl+вправо (тоже используем)
            b'\x1b[1;9C',  # Shift+Option+вправо
            b'\x1bOC',     # Альтернативный вариант
            '\x1b[1;3C',   # Строковый вариант
            '\x1b[1;5C',
            '\x1b[1;9C',
            '\x1bOC',
        ]
        
        # Проверяем Option+влево
        found_option_left = False
        for pattern in option_left_patterns:
            if isinstance(pattern, bytes):
                if pattern in key_bytes:
                    found_option_left = True
                    break
            else:
                if pattern in key_str:
                    found_option_left = True
                    break
        
        # Проверяем Option+вправо
        found_option_right = False
        for pattern in option_right_patterns:
            if isinstance(pattern, bytes):
                if pattern in key_bytes:
                    found_option_right = True
                    break
            else:
                if pattern in key_str:
                    found_option_right = True
                    break
        
        if found_option_left:
            logger.info(f"Moving cursor WORD LEFT (Option+Left), key_str={repr(key_str)}, key_name={key_name}")
            self.editor.move_cursor_word_left()
            return  # Важно: return чтобы не обрабатывать как обычную стрелку
        
        if found_option_right:
            logger.info(f"Moving cursor WORD RIGHT (Option+Right), key_str={repr(key_str)}, key_name={key_name}")
            self.editor.move_cursor_word_right()
            return  # Важно: return чтобы не обрабатывать как обычную стрелку
        
        # Если не Option+стрелки, логируем для отладки
        if key_str.startswith('\x1b') and ('D' in key_str or 'C' in key_str):
            logger.info(f"Unhandled arrow sequence: key_str={repr(key_str)}, key_name={key_name}, key_code={key_code}, is_sequence={is_sequence}")
        
        # Отслеживаем быстрое повторение стрелок для перемещения по словам
        # Если стрелка влево/вправо нажимается быстро (< 170ms) после предыдущей такой же стрелки,
        # это означает перемещение по словам (Option+стрелка)
        import time
        current_time = time.time()
        
        # Проверяем Shift+стрелки для выделения текста
        # blessed может определять Shift+стрелки как KEY_SUP, KEY_SDOWN, KEY_SLEFT, KEY_SRIGHT
        # Также Shift+стрелки отправляют ESC-последовательности с модификатором 2 (Shift)
        # \x1b[1;2A - Shift+Up
        # \x1b[1;2B - Shift+Down  
        # \x1b[1;2D - Shift+Left
        # \x1b[1;2C - Shift+Right
        
        # Сначала проверяем имена клавиш blessed (KEY_SUP, KEY_SDOWN, KEY_SLEFT, KEY_SRIGHT)
        found_shift_arrow = False
        shift_direction = None
        
        if key_name == 'KEY_SUP' or key_name == 'KEY_S_UP':
            found_shift_arrow = True
            shift_direction = 'UP'
            logger.info(f"Found Shift+UP via key_name: {key_name}, key_str={repr(key_str)}")
        elif key_name == 'KEY_SDOWN' or key_name == 'KEY_S_DOWN':
            found_shift_arrow = True
            shift_direction = 'DOWN'
            logger.info(f"Found Shift+DOWN via key_name: {key_name}, key_str={repr(key_str)}")
        elif key_name == 'KEY_SLEFT' or key_name == 'KEY_S_LEFT':
            found_shift_arrow = True
            shift_direction = 'LEFT'
            logger.info(f"Found Shift+LEFT via key_name: {key_name}, key_str={repr(key_str)}")
        elif key_name == 'KEY_SRIGHT' or key_name == 'KEY_S_RIGHT':
            found_shift_arrow = True
            shift_direction = 'RIGHT'
            logger.info(f"Found Shift+RIGHT via key_name: {key_name}, key_str={repr(key_str)}")
        
        # Если не нашли через key_name, проверяем ESC-последовательности
        if not found_shift_arrow:
            shift_arrow_patterns = [
                # Стандартные последовательности с модификатором 2 (проверяем ПЕРВЫМИ - они наиболее вероятны)
                ('\x1b[1;2A', 'UP'), (b'\x1b[1;2A', 'UP'),
                ('\x1b[1;2B', 'DOWN'), (b'\x1b[1;2B', 'DOWN'),
                ('\x1b[1;2D', 'LEFT'), (b'\x1b[1;2D', 'LEFT'),
                ('\x1b[1;2C', 'RIGHT'), (b'\x1b[1;2C', 'RIGHT'),
                # Альтернативные последовательности
                ('\x1b[2A', 'UP'), (b'\x1b[2A', 'UP'),
                ('\x1b[2B', 'DOWN'), (b'\x1b[2B', 'DOWN'),
                ('\x1b[2D', 'LEFT'), (b'\x1b[2D', 'LEFT'),
                ('\x1b[2C', 'RIGHT'), (b'\x1b[2C', 'RIGHT'),
                # С префиксом O
                ('\x1bO2A', 'UP'), (b'\x1bO2A', 'UP'),
                ('\x1bO2B', 'DOWN'), (b'\x1bO2B', 'DOWN'),
                ('\x1bO2D', 'LEFT'), (b'\x1bO2D', 'LEFT'),
                ('\x1bO2C', 'RIGHT'), (b'\x1bO2C', 'RIGHT'),
            ]
            
            # Проверяем все варианты последовательностей
            # Важно: проверяем как точное совпадение, так и startswith для строк, и in/startswith для bytes
            for pattern, direction in shift_arrow_patterns:
                if isinstance(pattern, bytes):
                    # Для bytes проверяем включение и начало
                    if pattern in key_bytes or key_bytes.startswith(pattern):
                        found_shift_arrow = True
                        shift_direction = direction
                        logger.info(f"Found Shift+{direction} pattern (bytes): {repr(pattern)}, key_str={repr(key_str)}, key_bytes={repr(key_bytes)}")
                        break
                else:
                    # Для строк проверяем включение и начало
                    if pattern in key_str or key_str.startswith(pattern):
                        found_shift_arrow = True
                        shift_direction = direction
                        logger.info(f"Found Shift+{direction} pattern (str): {repr(pattern)}, key_str={repr(key_str)}")
                        break
            
            # Дополнительная проверка: может быть последовательность передана как часть key_str
            # Проверяем если key_str начинается с ESC и содержит соответствующий паттерн
            # Важно: проверяем ПЕРЕД обычными стрелками, чтобы не перехватить их
            if not found_shift_arrow:
                # Проверяем последовательности для Shift+Up/Down более тщательно
                # На macOS терминал может отправлять разные варианты
                if key_str.startswith('\x1b[') or key_str.startswith('\x1bO'):
                    # Проверяем Shift+Up (может быть \x1b[1;2A, \x1b[2A, \x1bO2A и т.д.)
                    if '1;2A' in key_str or ('2A' in key_str and key_str.startswith('\x1b[')) or 'O2A' in key_str:
                        # Но исключаем обычные стрелки - если это просто \x1b[A без 2, то это обычная стрелка
                        if not (key_str == '\x1b[A' or key_str == '\x1bOA'):
                            found_shift_arrow = True
                            shift_direction = 'UP'
                            logger.info(f"Found Shift+UP via partial match in key_str: {repr(key_str)}")
                    # Проверяем Shift+Down
                    elif '1;2B' in key_str or ('2B' in key_str and key_str.startswith('\x1b[')) or 'O2B' in key_str:
                        if not (key_str == '\x1b[B' or key_str == '\x1bOB'):
                            found_shift_arrow = True
                            shift_direction = 'DOWN'
                            logger.info(f"Found Shift+DOWN via partial match in key_str: {repr(key_str)}")
                    # Проверяем Shift+Left
                    elif '1;2D' in key_str or ('2D' in key_str and key_str.startswith('\x1b[')) or 'O2D' in key_str:
                        if not (key_str == '\x1b[D' or key_str == '\x1bOD'):
                            found_shift_arrow = True
                            shift_direction = 'LEFT'
                            logger.info(f"Found Shift+LEFT via partial match in key_str: {repr(key_str)}")
                    # Проверяем Shift+Right
                    elif '1;2C' in key_str or ('2C' in key_str and key_str.startswith('\x1b[')) or 'O2C' in key_str:
                        if not (key_str == '\x1b[C' or key_str == '\x1bOC'):
                            found_shift_arrow = True
                            shift_direction = 'RIGHT'
                            logger.info(f"Found Shift+RIGHT via partial match in key_str: {repr(key_str)}")
        
        if found_shift_arrow:
            self._last_arrow_key = None
            logger.info(f"Processing Shift+{shift_direction} for selection, key_str={repr(key_str)}, key_bytes={repr(key_bytes)}")
            # Используем встроенные методы prompt_toolkit для выделения
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.enter_shift_mode()
                except (AttributeError, TypeError):
                    logger.debug("Failed to enter shift mode")
            # Перемещаем курсор для расширения выделения
            if shift_direction == 'UP':
                self.editor.move_cursor_up()
            elif shift_direction == 'DOWN':
                self.editor.move_cursor_down()
            elif shift_direction == 'LEFT':
                self.editor.move_cursor_left()
            elif shift_direction == 'RIGHT':
                self.editor.move_cursor_right()
            # Запоминаем время последнего Shift+Right/Left для возможности продолжения выделения через Up/Down
            if shift_direction in ('LEFT', 'RIGHT'):
                import time
                self._last_shift_arrow_time = time.time()
            logger.debug(f"Selection extended via prompt_toolkit, cursor={self.editor.buffer.cursor_position}")
            return
        
        # Дополнительная проверка: если выделение уже начато, то любые стрелки продолжают выделение
        # Это нужно для случая, когда Shift+Up/Down не определяются терминалом
        # Также проверяем, не было ли недавно Shift+Right/Left - тогда Up/Down могут быть Shift+Up/Down
        import time
        current_time = time.time()
        time_since_shift_arrow = current_time - self._last_shift_arrow_time if self._last_shift_arrow_time > 0 else float('inf')
        
        if (key_name == 'KEY_UP' or key_name == 'KEY_DOWN'):
            # Проверяем, недавно ли был Shift+Right/Left - тогда Up/Down могут быть Shift+Up/Down
            should_continue_selection = time_since_shift_arrow < self._shift_arrow_timeout
            
            if should_continue_selection:
                # Используем встроенные методы prompt_toolkit для выделения
                if self.editor.buffer.selection_state is not None:
                    try:
                        self.editor.buffer.selection_state.enter_shift_mode()
                    except (AttributeError, TypeError):
                        logger.debug("Failed to enter shift mode")
                
                logger.info(f"Continuing selection with {key_name} (recent Shift+arrow detected, time_since={time_since_shift_arrow*1000:.1f}ms)")
                self._last_arrow_key = None
                if key_name == 'KEY_UP':
                    self.editor.move_cursor_up()
                elif key_name == 'KEY_DOWN':
                    self.editor.move_cursor_down()
                # Сбрасываем таймер после использования
                self._last_shift_arrow_time = 0
                return
        
        # Обычные стрелки для перемещения курсора
        # ВАЖНО: проверяем обычные стрелки ПОСЛЕ Shift+стрелок, чтобы не перехватить их
        
        if key_name == 'KEY_UP' or key_str == '\x1b[A':  # ESC[A - стрелка вверх
            # Выключаем режим выделения если он активен
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.leave_shift_mode()
                except (AttributeError, TypeError):
                    pass
            
            # Сбрасываем отслеживание стрелок влево/вправо при нажатии вверх/вниз
            self._last_arrow_key = None
            logger.debug("Moving cursor UP")
            self.editor.move_cursor_up()
        elif key_name == 'KEY_DOWN' or key_str == '\x1b[B':  # ESC[B - стрелка вниз
            # Выключаем режим выделения если он активен
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.leave_shift_mode()
                except (AttributeError, TypeError):
                    pass
            
            # Сбрасываем отслеживание стрелок влево/вправо при нажатии вверх/вниз
            self._last_arrow_key = None
            logger.debug("Moving cursor DOWN")
            self.editor.move_cursor_down()
        elif key_name == 'KEY_LEFT' or key_str == '\x1b[D':  # ESC[D - стрелка влево
            # Выключаем режим выделения если он активен
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.leave_shift_mode()
                except (AttributeError, TypeError):
                    pass
            
            # Проверяем, не было ли это быстрое повторное нажатие той же стрелки
            if (self._last_arrow_key == 'KEY_LEFT' and
                self._last_arrow_time > 0):
                time_since_last = current_time - self._last_arrow_time
                if time_since_last < 0.17:  # Если нажата быстро (< 170ms) после предыдущей стрелки
                    logger.info(f"Moving cursor WORD LEFT (fast arrow repeat), time_since_last={time_since_last*1000:.1f}ms")
                    self.editor.move_cursor_word_left()
                    self._last_arrow_time = current_time
                    return
            
            # Обычное перемещение по одному символу
            logger.debug("Moving cursor LEFT")
            self.editor.move_cursor_left()
            self._last_arrow_key = 'KEY_LEFT'
            self._last_arrow_time = current_time
            
        elif key_name == 'KEY_RIGHT' or key_str == '\x1b[C':  # ESC[C - стрелка вправо
            # Выключаем режим выделения если он активен
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.leave_shift_mode()
                except (AttributeError, TypeError):
                    pass
            
            # Проверяем, не было ли это быстрое повторное нажатие той же стрелки
            if (self._last_arrow_key == 'KEY_RIGHT' and
                self._last_arrow_time > 0):
                time_since_last = current_time - self._last_arrow_time
                if time_since_last < 0.17:  # Если нажата быстро (< 170ms) после предыдущей стрелки
                    logger.info(f"Moving cursor WORD RIGHT (fast arrow repeat), time_since_last={time_since_last*1000:.1f}ms")
                    self.editor.move_cursor_word_right()
                    self._last_arrow_time = current_time
                    return
            
            # Обычное перемещение по одному символу
            logger.debug("Moving cursor RIGHT")
            self.editor.move_cursor_right()
            self._last_arrow_key = 'KEY_RIGHT'
            self._last_arrow_time = current_time
        
        # Enter - новая строка
        elif key_name == 'KEY_ENTER' or key_str == '\n' or key_str == '\r':
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            # Выключаем режим выделения
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.leave_shift_mode()
                except (AttributeError, TypeError):
                    pass
            logger.debug("Inserting newline")
            self.editor.insert_newline()
        
        # Backspace - удалить символ слева
        elif key_name == 'KEY_BACKSPACE' or key_str == '\x7f' or key_str == '\b':
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            # Выключаем режим выделения
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.leave_shift_mode()
                except (AttributeError, TypeError):
                    pass
            logger.debug("Deleting character backward")
            self.editor.delete_char_backward()
        
        # Delete - удалить символ справа
        elif key_name == 'KEY_DELETE' or key_str == '\x1b[3~':
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            # Выключаем режим выделения
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.leave_shift_mode()
                except (AttributeError, TypeError):
                    pass
            logger.debug("Deleting character forward")
            self.editor.delete_char_forward()
        
        # Tab - табуляция
        elif key_name == 'KEY_TAB' or key_str == '\t':
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            # Выключаем режим выделения
            if self.editor.buffer.selection_state is not None:
                try:
                    self.editor.buffer.selection_state.leave_shift_mode()
                except (AttributeError, TypeError):
                    pass
            logger.debug("Inserting tab")
            self.editor.insert_tab(tab_size=4)
        
        # Command+C/X/V - копирование/вырезание/вставка
        # На macOS терминал может перехватывать Ctrl+C, поэтому Command+C может не доходить до приложения
        # Проверяем различные варианты: key_code, key_str, и возможные последовательности
        
        # Command+C - копирование (\x03 или key_code == 3)
        # ВАЖНО: Проверяем ПЕРЕД обработкой обычных символов, но ПОСЛЕ всех других специальных клавиш
        if key_str == '\x03' or key_code == 3:  # Ctrl+C / Command+C
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            logger.info(f"Copy command detected: name={key_name}, code={key_code}, str={repr(key_str)}")
            if self.editor.copy_selected_text():
                logger.info("Text copied to clipboard successfully")
            else:
                logger.warning("Copy failed: no selection or clipboard error")
            # НЕ очищаем выделение после копирования
            return
        
        # Command+X - вырезание (\x18 или key_code == 24)
        elif key_str == '\x18' or key_code == 24:  # Ctrl+X / Command+X
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            logger.info(f"Cut command detected: name={key_name}, code={key_code}, str={repr(key_str)}")
            if self.editor.cut_selected_text():
                logger.info("Text cut and copied to clipboard successfully")
            else:
                logger.warning("Cut failed: no selection or clipboard error")
            return
        
        # Command+V - вставка (\x16 или key_code == 22)
        elif key_str == '\x16' or key_code == 22:  # Ctrl+V / Command+V
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            logger.info(f"Paste command detected: name={key_name}, code={key_code}, str={repr(key_str)}")
            if self.editor.paste_text():
                logger.info("Text pasted from clipboard successfully")
            else:
                logger.warning("Paste failed: clipboard is empty or paste error")
            return
        
        # ВАЖНО: На macOS терминал может перехватывать Ctrl+C/X/V, поэтому Command+C/X/V могут не доходить до приложения
        # Добавляем логирование ВСЕХ клавиш, чтобы увидеть, что приходит при нажатии Command+C/X/V
        # Логируем любые подозрительные клавиши (управляющие символы)
        if len(key_str) == 1 and ord(key_str) < 32:
            logger.info(f"Control character detected: name={key_name}, code={key_code}, str={repr(key_str)}, ord={ord(key_str)}")
        
        # Обычные символы - вставка
        else:
            # Проверяем что это обычный печатаемый символ
            # Пропускаем управляющие последовательности и ESC-коды
            if (len(key_str) == 1 and 
                ord(key_str) >= 32 and 
                ord(key_str) != 127 and
                not key_str.startswith('\x1b')):
                # Сбрасываем отслеживание стрелок при вводе текста
                self._last_arrow_key = None
                # Выключаем режим выделения при вводе текста
                if self.editor.buffer.selection_state is not None:
                    try:
                        self.editor.buffer.selection_state.leave_shift_mode()
                    except (AttributeError, TypeError):
                        pass
                logger.debug(f"Inserting character: {repr(key_str)}")
                self.editor.insert_char(key_str)
            else:
                logger.debug(f"Unhandled key in editor: name={key_name}, code={key_code}, str={repr(key_str)}")

    def _confirm_delete(self, terminal) -> bool:
        """
        ??Очистка экранаОчистка экрана?? Выход?

        Args:
            terminal: Выход?? blessed.Terminal

        Returns:
            True если подтверждено, False иначе
        """
        # ВыходВыход: просто вернём True
        # TODO: ВыходОчистка экрана Временно???
        return True

    def run(self) -> None:
        """Выход?? Временно"""
        terminal = self.term_manager.get_terminal()

        try:
            # Выход ? Временно??? Выход?
            print(self.term_manager.enter_fullscreen(), end="")
            print(self.term_manager.hide_cursor(), end="")

            self.running = True

            # ??Очистка экрана???
            self._render_with_status()

            # ВыходВыход Выход ??Очистка экрана?
            with terminal.cbreak(), terminal.hidden_cursor():
                while self.running:
                    # ?Очистка экрана??? ?Очистка экрана???
                    if self.term_manager.has_size_changed():
                        # ?Очистка экрана? ? Временно??
                        self.refresh()
                        self._render_with_status()

                    # Выход??Очистка экрана?? Выход?
                    inp = terminal.inkey(timeout=0.1)
                    
                    if inp:
                        # Временно? Выход Выход?? ??? Выход???
                        self._log_key(inp, "[ALL KEYS]")
                        
                        # Выход?
                        if inp.lower() == "q":
                            self.running = False
                            break
                        
                        # Tab - Выход?Очистка экрана
                        if inp == '\t' or (hasattr(inp, 'name') and inp.name == 'TAB'):
                            logger.debug("Tab pressed - toggling focus")
                            self._toggle_focus()
                            self._render_with_status()
                            continue
                        
                        # Обработка клавиш в зависимости от фокуса
                        if self.focused_pane == 'tree':
                            try:
                                self._handle_tree_key(inp)
                                self._render_with_status()
                            except Exception as e:
                                logger.error(f"Ошибка при обработке клавиши в дереве: {e}", exc_info=True)
                        elif self.focused_pane == 'editor':
                            try:
                                self._handle_editor_key(inp)
                                self._render_with_status()
                            except Exception as e:
                                logger.error(f"Ошибка при обработке клавиши в редакторе: {e}", exc_info=True)

        except KeyboardInterrupt:
            self.running = False
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            self.running = False
        finally:
            # Выход? ?? Выход???Очистка экрана ? Выход???Очистка экрана?
            print(self.term_manager.exit_fullscreen(), end="")
            print(self.term_manager.show_cursor(), end="")
            print(self.term_manager.clear(), end="")
            logger.info("Application closed")

    def refresh(self) -> None:
        """?Очистка экрана? ? Временно?? Выход?"""
        self.term_manager.refresh_size()
        width, height = self.term_manager.get_size()
        self.layout.update_size(width, height)
        # ?Очистка экрана? Выход???
        self.file_tree.x, self.file_tree.y, self.file_tree.width, self.file_tree.height = (
            self.layout.get_tree_bounds()
        )
        self.editor.x, self.editor.y, self.editor.width, self.editor.height = (
            self.layout.get_editor_bounds()
        )
