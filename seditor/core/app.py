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
        
        # Расширенное логирование для отладки Option+стрелок
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
        
        # Обычные стрелки для перемещения курсора
        if key_name == 'KEY_UP' or key_str == '\x1b[A':  # ESC[A - стрелка вверх
            # Сбрасываем отслеживание стрелок влево/вправо при нажатии вверх/вниз
            self._last_arrow_key = None
            logger.debug("Moving cursor UP")
            self.editor.move_cursor_up()
        elif key_name == 'KEY_DOWN' or key_str == '\x1b[B':  # ESC[B - стрелка вниз
            # Сбрасываем отслеживание стрелок влево/вправо при нажатии вверх/вниз
            self._last_arrow_key = None
            logger.debug("Moving cursor DOWN")
            self.editor.move_cursor_down()
        elif key_name == 'KEY_LEFT' or key_str == '\x1b[D':  # ESC[D - стрелка влево
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
            logger.debug("Inserting newline")
            self.editor.insert_newline()
        
        # Backspace - удалить символ слева
        elif key_name == 'KEY_BACKSPACE' or key_str == '\x7f' or key_str == '\b':
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            logger.debug("Deleting character backward")
            self.editor.delete_char_backward()
        
        # Delete - удалить символ справа
        elif key_name == 'KEY_DELETE' or key_str == '\x1b[3~':
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            logger.debug("Deleting character forward")
            self.editor.delete_char_forward()
        
        # Tab - табуляция
        elif key_name == 'KEY_TAB' or key_str == '\t':
            # Сбрасываем отслеживание стрелок
            self._last_arrow_key = None
            logger.debug("Inserting tab")
            self.editor.insert_tab(tab_size=4)
        
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
