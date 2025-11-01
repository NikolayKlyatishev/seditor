# -*- coding: utf-8 -*-
"""
Главное приложение seditor на основе prompt_toolkit.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.layout import Layout as PTKLayout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition
from prompt_toolkit.styles import Style, merge_styles, style_from_pygments_cls
from prompt_toolkit.lexers import DynamicLexer
from pygments.styles import get_style_by_name

from seditor.terminal.layout import Layout as ScreenLayout
from seditor.components.editor_ptk import EditorPanePTK
from seditor.components.file_tree import FileTreePane
from seditor.components.command_palette import CommandPalette
from seditor.search import SemanticIndexer

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='seditor_debug.log'
)
logger = logging.getLogger(__name__)


class AppPTK:
    """Основное приложение seditor, построенное на prompt_toolkit."""

    AUTOSAVE_INTERVAL = 5  # seconds

    def __init__(self) -> None:
        self.screen_layout = ScreenLayout(100, 30)
        self.file_tree_pane = FileTreePane(self.screen_layout)
        self.editor_pane = EditorPanePTK(self.screen_layout)
        self.command_palette = CommandPalette()

        self.focused_pane: str = 'tree'
        self.current_file: Optional[str] = None
        self._status_message: str = ''
        self._autosave_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._current_theme: str = 'vscode-dark'  # Текущая тема
        
        # Семантический индексатор
        self.semantic_indexer: Optional[SemanticIndexer] = None
        self._indexing_task: Optional[asyncio.Task] = None

        self.kb = KeyBindings()
        self._setup_keybindings()

        self.tree_control = FormattedTextControl(
            text=self._get_tree_content,
            focusable=True,
            show_cursor=False,
        )
        # Обработчик клика мыши для дерева файлов
        self.tree_control.mouse_handler = self._tree_mouse_handler
        
        self.tree_window = Window(
            content=self.tree_control,
            width=Dimension(weight=1, max=self.screen_layout.tree_width),
            style='class:tree',
            wrap_lines=False,
        )
        self.separator_window = Window(
            content=FormattedTextControl(text=lambda: '│'),
            width=Dimension.exact(1),
            style='class:separator',
        )
        self.editor_control = BufferControl(
            buffer=self.editor_pane.buffer,
            lexer=DynamicLexer(self._get_editor_lexer),
            focusable=True,
        )
        self.editor_window = Window(
            content=self.editor_control,
            width=Dimension(weight=3),
            style='class:editor',
            wrap_lines=False,
        )
        self.status_control = FormattedTextControl(text=self._get_status_text)
        self.status_window = Window(
            content=self.status_control,
            height=Dimension.exact(1),
            style='class:status',
        )
        
        # Командная палитра
        self.command_palette_control = FormattedTextControl(text=self._get_command_palette_text)
        self.command_palette_input = BufferControl(
            buffer=self.command_palette.buffer,
            focusable=True,
        )
        self.command_palette_window = Window(
            content=self.command_palette_control,
            height=lambda: Dimension.exact(min(12, len(self.command_palette.filtered_items) + 3)) if self.command_palette.is_visible else Dimension.exact(0),
            style='class:command_palette',
        )
        self.command_palette_input_window = Window(
            content=self.command_palette_input,
            height=Dimension.exact(1) if self.command_palette.is_visible else Dimension.exact(0),
            style='class:command_palette.input',
        )

        body = VSplit(
            [self.tree_window, self.separator_window, self.editor_window],
            padding=0,
        )
        container = HSplit([body, self.command_palette_window, self.command_palette_input_window, self.status_window])

        self.layout = PTKLayout(container, focused_element=self.tree_window)
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            style=self._create_style(),
            refresh_interval=0.5,
            mouse_support=True,  # Включаем поддержку мыши
        )
        self.app.pre_run_callables.append(self._on_app_start)

    def _on_app_start(self) -> None:
        self._running = True
        self._update_screen_layout_from_output()
        if self._autosave_task is None:
            self._autosave_task = self.app.create_background_task(self._autosave_loop())

    def _get_editor_lexer(self):
        """Возвращает лексер для редактора (вызывается BufferControl)."""
        return self.editor_pane.get_lexer()
    
    def _tree_mouse_handler(self, mouse_event):
        """Обработчик событий мыши для дерева файлов"""
        from prompt_toolkit.mouse_events import MouseEventType
        
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            # Переключаем фокус на дерево файлов при клике
            if self.focused_pane != 'tree':
                self._focus_tree()
            
            # Вычисляем на какую строку кликнули
            clicked_line = mouse_event.position.y
            
            # Получаем список видимых элементов
            visible_items = self.file_tree_pane.get_visible_items()
            
            if 0 <= clicked_line < len(visible_items):
                target_item = visible_items[clicked_line]
                
                # Устанавливаем выделение на кликнутый элемент
                self.file_tree_pane.tree.selected_node = target_item
                
                # Обрабатываем клик
                if not target_item.is_dir:
                    # Файл - открываем его
                    self._open_file(target_item.path)
                else:
                    # Директория - разворачиваем/сворачиваем
                    target_item.expanded = not target_item.expanded
                
                self.app.invalidate()

    def _update_screen_layout_from_output(self) -> None:
        output = getattr(self.app, 'output', None)
        if output is None:
            return
        size = output.get_size()
        if (
            size.columns != self.screen_layout.terminal_width
            or size.rows != self.screen_layout.terminal_height
        ):
            self.screen_layout.update_size(size.columns, size.rows)

    def _create_style(self) -> Style:
        # Выбираем тему в зависимости от настройки
        if self._current_theme == 'vscode-dark':
            # Наша кастомная тема VS Code Dark+
            pygments_style = Style([])
            syntax_colors = [
                ('pygments.keyword', 'fg:#c586c0'),
                ('pygments.keyword.namespace', 'fg:#c586c0'),
                ('pygments.keyword.type', 'fg:#4ec9b0'),
                ('pygments.name', 'fg:#9cdcfe'),
                ('pygments.name.builtin', 'fg:#4ec9b0'),
                ('pygments.name.function', 'fg:#dcdcaa'),
                ('pygments.name.class', 'fg:#4ec9b0'),
                ('pygments.name.decorator', 'fg:#dcdcaa'),
                ('pygments.string', 'fg:#ce9178'),
                ('pygments.string.doc', 'fg:#6a9955'),
                ('pygments.number', 'fg:#b5cea8'),
                ('pygments.comment', 'fg:#6a9955'),
                ('pygments.comment.single', 'fg:#6a9955'),
                ('pygments.comment.multiline', 'fg:#6a9955'),
                ('pygments.operator', 'fg:#d4d4d4'),
                ('pygments.punctuation', 'fg:#d4d4d4'),
                ('pygments.literal', 'fg:#569cd6'),
                ('pygments.literal.string', 'fg:#ce9178'),
            ]
        else:
            # Стандартная тема Pygments
            try:
                pygments_style = style_from_pygments_cls(get_style_by_name(self._current_theme))
                syntax_colors = []
            except Exception:
                # Если тема не найдена, используем нашу кастомную
                pygments_style = Style([])
                syntax_colors = [
                    ('pygments.keyword', 'fg:#c586c0'),
                    ('pygments.name.function', 'fg:#dcdcaa'),
                    ('pygments.string', 'fg:#ce9178'),
                    ('pygments.comment', 'fg:#6a9955'),
                ]
        
        # Базовые стили для UI
        ui_style = Style([
            # Дерево файлов
            ('tree', 'bg:#1e1e1e fg:#d4d4d4'),
            ('tree.header', 'fg:#888'),
            ('tree.text', 'fg:#d4d4d4'),
            ('tree.selected', 'fg:#d4d4d4'),
            ('tree.selected.focused', 'bg:#3a3d41 fg:#ffffff'),
            ('tree.empty', 'fg:#666'),
            ('separator', 'fg:#444'),
            
            # Редактор
            ('editor', 'bg:#1e1e1e fg:#d4d4d4'),
            ('editor.line-number', '#858585'),
            ('editor.cursor', 'bg:#aeafad'),
            ('editor.selection', 'bg:#264f78'),
            
            # Статус-бар
            ('status', 'bg:#1b1b1b fg:#d4d4d4'),
            ('status.label', 'bold'),
            ('status.separator', 'fg:#555'),
            ('status.message', 'fg:#9cdcfe'),
            ('status.hint', 'fg:#888 italic'),
            
            # Командная палитра
            ('command_palette', 'bg:#252526 fg:#cccccc'),
            ('command_palette.header', 'bg:#252526 fg:#ffffff bold'),
            ('command_palette.separator', 'bg:#252526 fg:#555'),
            ('command_palette.item', 'bg:#252526 fg:#cccccc'),
            ('command_palette.selected', 'bg:#094771 fg:#ffffff bold'),
            ('command_palette.empty', 'bg:#252526 fg:#888 italic'),
            ('command_palette.input', 'bg:#3c3c3c fg:#cccccc'),
        ] + syntax_colors)
        
        return merge_styles([pygments_style, ui_style])

    def _get_tree_content(self) -> FormattedText:
        self._update_screen_layout_from_output()
        render_info = getattr(self.tree_window, 'render_info', None)
        if render_info:
            width_limit = max(0, render_info.window_width - 2)
            available_lines = max(0, render_info.window_height - 1)
            self.file_tree_pane.width = render_info.window_width
            self.file_tree_pane.height = render_info.window_height
        else:
            width_limit = max(0, self.screen_layout.tree_width - 2)
            available_lines = max(0, self.screen_layout.height - 1)

        current_path = getattr(self.file_tree_pane.tree, 'current_path', '')
        header = os.path.basename(current_path) or current_path or 'Файлы'

        fragments: list[tuple[str, str]] = [
            ('class:tree.header', header),
            ('', '\n'),
        ]

        lines = self.file_tree_pane.get_display_lines(
            max_lines=available_lines,
            max_width=width_limit,
        )

        if not lines:
            fragments.append(('class:tree.empty', '  <пусто>'))
            return FormattedText(fragments)

        padding_width = max(0, width_limit + 2)
        for idx, (name, is_selected) in enumerate(lines):
            indicator = '▶ ' if is_selected else '  '
            if is_selected:
                style = 'class:tree.selected.focused' if self.focused_pane == 'tree' else 'class:tree.selected'
            else:
                style = 'class:tree.text'
            line = f'{indicator}{name}'.ljust(padding_width)
            fragments.append((style, line))
            if idx < len(lines) - 1:
                fragments.append(('', '\n'))

        return FormattedText(fragments)

    def _get_status_text(self) -> FormattedText:
        fragments: list[tuple[str, str]] = []
        file_path = self.editor_pane.get_file_path()
        if file_path:
            filename = os.path.basename(file_path)
            marker = '*' if self.editor_pane.has_unsaved_changes() else ''
            fragments.append(('class:status.label', f'Файл: {filename}{marker}'))
        else:
            fragments.append(('class:status.label', 'Файл: <не открыт>'))

        if self._status_message:
            fragments.append(('class:status.separator', ' | '))
            fragments.append(('class:status.message', self._status_message))
        
        # Показываем подсказку о командной палитре
        if not self.command_palette.is_visible:
            fragments.append(('class:status.separator', ' | '))
            fragments.append(('class:status.hint', 'Ctrl+P - команды'))

        return FormattedText(fragments)
    
    def _get_command_palette_text(self) -> FormattedText:
        """Отрисовка командной палитры"""
        if not self.command_palette.is_visible:
            return FormattedText([])
        
        fragments: list[tuple[str, str]] = []
        
        # Заголовок
        if self.command_palette.mode == 'command':
            header = '  Команды (введите для поиска):'
        elif self.command_palette.mode == 'theme_select':
            header = '  Выберите тему:'
        elif self.command_palette.mode == 'search':
            header = '  Поиск файлов (введите описание):'
        else:
            header = '  Команды:'
        
        fragments.append(('class:command_palette.header', header))
        fragments.append(('', '\n'))
        fragments.append(('class:command_palette.separator', '─' * 60))
        fragments.append(('', '\n'))
        
        # Список команд/тем/файлов
        lines = self.command_palette.get_display_lines(max_lines=10)
        for name, is_selected in lines:
            if is_selected:
                fragments.append(('class:command_palette.selected', f'▶ {name}'))
            else:
                fragments.append(('class:command_palette.item', f'  {name}'))
            fragments.append(('', '\n'))
        
        if not lines:
            if self.command_palette.mode == 'search':
                fragments.append(('class:command_palette.empty', '  Ничего не найдено по запросу'))
            else:
                fragments.append(('class:command_palette.empty', '  Ничего не найдено'))
            fragments.append(('', '\n'))
        
        return FormattedText(fragments)

    def _set_status(self, message: str, with_timestamp: bool = False) -> None:
        if with_timestamp and message:
            timestamp = datetime.now().strftime('%H:%M:%S')
            message = f'{message} {timestamp}'
        self._status_message = message
        if getattr(self, 'app', None) is not None and self.app.is_running:
            self.app.invalidate()

    def _focus_tree(self) -> None:
        self.focused_pane = 'tree'
        self.layout.focus(self.tree_window)
        if self.app.is_running:
            self.app.invalidate()

    def _focus_editor(self) -> None:
        self.focused_pane = 'editor'
        self.layout.focus(self.editor_window)
        if self.app.is_running:
            self.app.invalidate()

    def _toggle_focus(self) -> None:
        if self.focused_pane == 'tree':
            self._focus_editor()
        else:
            self._focus_tree()

    def _open_file(self, path: str) -> None:
        if self.editor_pane.load_file(path):
            self.current_file = path
            self._focus_editor()
            self._set_status(f'Открыт {os.path.basename(path)}')
        else:
            self._set_status('Не удалось открыть файл')
    
    def _open_file_and_reveal(self, path: str) -> None:
        """
        Открыть файл и раскрыть дерево до него
        
        Args:
            path: Путь к файлу
        """
        # Открываем файл
        if self.editor_pane.load_file(path):
            self.current_file = path
            # Раскрываем дерево до файла
            if self.file_tree_pane.reveal_path(path):
                self._set_status(f'Открыт {os.path.basename(path)}')
            else:
                self._set_status(f'Открыт {os.path.basename(path)} (файл вне текущего дерева)')
            self._focus_editor()
        else:
            self._set_status('Не удалось открыть файл')

    def _setup_keybindings(self) -> None:
        command_palette_visible = Condition(lambda: self.command_palette.is_visible)
        command_palette_hidden = Condition(lambda: not self.command_palette.is_visible)
        
        # Ctrl+P - открыть командную палитру
        @self.kb.add('c-p', filter=command_palette_hidden)
        def _(event) -> None:
            self.command_palette.show()
            self.layout.focus(self.command_palette_input_window)
            event.app.invalidate()
        
        # Escape - закрыть командную палитру
        @self.kb.add('escape', filter=command_palette_visible)
        def _(event) -> None:
            self.command_palette.hide()
            if self.focused_pane == 'tree':
                self.layout.focus(self.tree_window)
            else:
                self.layout.focus(self.editor_window)
            event.app.invalidate()
        
        # Enter - выбрать команду/тему
        @self.kb.add('enter', filter=command_palette_visible)
        def _(event) -> None:
            self._handle_command_palette_enter()
            event.app.invalidate()
        
        # Up/Down - навигация в командной палитре
        @self.kb.add('up', filter=command_palette_visible)
        def _(event) -> None:
            self.command_palette.move_up()
            event.app.invalidate()
        
        @self.kb.add('down', filter=command_palette_visible)
        def _(event) -> None:
            self.command_palette.move_down()
            event.app.invalidate()
        
        # Обработка изменения текста в командной палитре
        self.command_palette.buffer.on_text_changed += lambda _: self._on_command_palette_text_changed()
        
        @self.kb.add('tab', filter=command_palette_hidden)
        def _(event) -> None:
            self._toggle_focus()

        @self.kb.add('q', filter=command_palette_hidden)
        def _(event) -> None:
            self._request_exit()

        tree_focus = Condition(lambda: self.focused_pane == 'tree' and not self.command_palette.is_visible)
        editor_focus = Condition(lambda: self.focused_pane == 'editor' and not self.command_palette.is_visible)

        @self.kb.add('enter', filter=tree_focus)
        def _(event) -> None:
            result = self.file_tree_pane.enter()
            if result:
                self._open_file(result)
            else:
                # Вошли в директорию - запускаем индексацию
                current_path = self.file_tree_pane.tree.current_path
                self._set_status(
                    os.path.basename(current_path) or current_path
                )
                # Запускаем индексацию в фоне
                self._start_indexing(current_path)

        @self.kb.add('up', filter=tree_focus)
        def _(event) -> None:
            self.file_tree_pane.move_up()
            event.app.invalidate()

        @self.kb.add('down', filter=tree_focus)
        def _(event) -> None:
            self.file_tree_pane.move_down()
            event.app.invalidate()

        @self.kb.add('left', filter=tree_focus)
        def _(event) -> None:
            self.file_tree_pane.collapse_directory()
            event.app.invalidate()

        @self.kb.add('right', filter=tree_focus)
        def _(event) -> None:
            self.file_tree_pane.expand_directory()
            event.app.invalidate()

        @self.kb.add('backspace', filter=tree_focus)
        def _(event) -> None:
            self.file_tree_pane.go_up_level()
            event.app.invalidate()

        @self.kb.add('c-s', filter=editor_focus)
        def _(event) -> None:
            self._manual_save()

        # Option+Left (Alt+B в Emacs) - к началу предыдущего слова
        @self.kb.add('escape', 'b', filter=editor_focus)
        def _(event) -> None:
            buffer = event.app.current_buffer
            pos = buffer.document.find_start_of_previous_word()
            if pos:
                buffer.cursor_position += pos

        # Option+Right (Alt+F в Emacs) - к началу следующего слова
        @self.kb.add('escape', 'f', filter=editor_focus)
        def _(event) -> None:
            buffer = event.app.current_buffer
            pos = buffer.document.find_next_word_beginning()
            if pos:
                buffer.cursor_position += pos

    def _save_if_needed(self, message: str, force_timestamp: bool = True) -> bool:
        file_path = self.editor_pane.get_file_path()
        if not file_path:
            return False
        if not self.editor_pane.has_unsaved_changes():
            return False
        success = self.editor_pane.save_file()
        if success:
            self._set_status(message, with_timestamp=force_timestamp)
            logger.debug('File saved: %s', file_path)
        else:
            self._set_status('Ошибка сохранения')
            logger.error('Failed to save file: %s', file_path)
        return success

    def _manual_save(self) -> None:
        if not self.editor_pane.get_file_path():
            self._set_status('Нет файла для сохранения')
            return
        if not self.editor_pane.has_unsaved_changes():
            self._set_status('Изменений нет')
            return
        self._save_if_needed('Сохранено вручную')
    
    def _on_command_palette_text_changed(self) -> None:
        """Обработчик изменения текста в командной палитре"""
        self.command_palette.on_text_changed()
        
        # Если в режиме поиска - выполняем поиск
        if self.command_palette.mode == 'search':
            query = self.command_palette.buffer.text
            if query and len(query.strip()) > 0:
                self._perform_search(query)
            else:
                self.command_palette.set_search_results([])
        
        if self.app.is_running:
            self.app.invalidate()
    
    def _handle_command_palette_enter(self) -> None:
        """Обработка Enter в командной палитре"""
        selected = self.command_palette.get_selected_command()
        
        if not selected:
            return
        
        if self.command_palette.mode == 'command':
            # Режим выбора команды
            if selected == 'search':
                self.command_palette._enter_search()
            elif selected == 'themes':
                self.command_palette._enter_theme_select()
            elif selected == 'reindex':
                self._manual_reindex()
                self.command_palette.hide()
                if self.focused_pane == 'tree':
                    self.layout.focus(self.tree_window)
                else:
                    self.layout.focus(self.editor_window)
            elif selected == 'save':
                self._manual_save()
                self.command_palette.hide()
                if self.focused_pane == 'tree':
                    self.layout.focus(self.tree_window)
                else:
                    self.layout.focus(self.editor_window)
            elif selected == 'quit':
                self._request_exit()
        
        elif self.command_palette.mode == 'theme_select':
            # Режим выбора темы
            self._change_theme(selected)
            self.command_palette.hide()
            if self.focused_pane == 'tree':
                self.layout.focus(self.tree_window)
            else:
                self.layout.focus(self.editor_window)
        
        elif self.command_palette.mode == 'search':
            # Режим поиска файлов - selected это путь к файлу
            self._open_file_and_reveal(selected)
            self.command_palette.hide()
            self.layout.focus(self.editor_window)
    
    def _change_theme(self, theme_id: str) -> None:
        """Сменить тему подсветки синтаксиса"""
        self._current_theme = theme_id
        
        # Пересоздаём стиль с новой темой
        self.app.style = self._create_style()
        
        # Находим название темы для сообщения
        theme_name = theme_id
        for name, tid in CommandPalette.AVAILABLE_THEMES:
            if tid == theme_id:
                theme_name = name
                break
        
        self._set_status(f'Тема изменена: {theme_name}')
        logger.info(f'Theme changed to: {theme_id}')
    
    def _start_indexing(self, directory_path: str) -> None:
        """
        Запустить индексацию директории в фоне
        
        Args:
            directory_path: Путь к директории для индексации
        """
        # Отменяем предыдущую задачу индексации если есть
        if self._indexing_task and not self._indexing_task.done():
            self._indexing_task.cancel()
        
        # Создаём индексатор если ещё не создан или путь изменился
        if self.semantic_indexer is None or self.semantic_indexer.root_path != directory_path:
            try:
                self.semantic_indexer = SemanticIndexer(directory_path)
                logger.info(f'Created semantic indexer for: {directory_path}')
            except Exception as e:
                logger.error(f'Failed to create indexer: {e}')
                self._set_status('Ошибка создания индексатора')
                return
        
        # Проверяем, нужна ли индексация
        if self.semantic_indexer.is_indexed():
            count = self.semantic_indexer.get_indexed_count()
            self._set_status(f'Индекс готов ({count} файлов)')
            return
        
        # Запускаем индексацию в фоне
        self._indexing_task = self.app.create_background_task(self._index_directory_async())
    
    async def _index_directory_async(self) -> None:
        """Асинхронная индексация директории"""
        try:
            self._set_status('Индексация...')
            
            def progress_callback(current: int, total: int):
                """Обновление прогресса индексации"""
                self._set_status(f'Индексация: {current}/{total} файлов')
                if self.app.is_running:
                    self.app.invalidate()
            
            # Запускаем индексацию в executor чтобы не блокировать UI
            loop = asyncio.get_event_loop()
            indexed_count = await loop.run_in_executor(
                None,
                lambda: self.semantic_indexer.index_directory(progress_callback)
            )
            
            self._set_status(f'Индексация завершена ({indexed_count} файлов)')
            logger.info(f'Indexing completed: {indexed_count} files')
            
        except asyncio.CancelledError:
            self._set_status('Индексация отменена')
            logger.info('Indexing cancelled')
        except Exception as e:
            self._set_status('Ошибка индексации')
            logger.error(f'Indexing failed: {e}', exc_info=True)
    
    def _perform_search(self, query: str) -> None:
        """
        Выполнить семантический поиск
        
        Args:
            query: Поисковый запрос
        """
        if self.semantic_indexer is None:
            self.command_palette.set_search_results([])
            return
        
        try:
            results = self.semantic_indexer.search(query, top_k=10)
            self.command_palette.set_search_results(results)
        except Exception as e:
            logger.error(f'Search failed: {e}')
            self.command_palette.set_search_results([])
    
    def _manual_reindex(self) -> None:
        """Ручная переиндексация текущей директории"""
        current_path = self.file_tree_pane.tree.current_path
        
        # Пересоздаём индексатор
        try:
            self.semantic_indexer = SemanticIndexer(current_path)
            logger.info(f'Recreated semantic indexer for reindexing: {current_path}')
        except Exception as e:
            logger.error(f'Failed to create indexer: {e}')
            self._set_status('Ошибка создания индексатора')
            return
        
        # Запускаем индексацию
        self._indexing_task = self.app.create_background_task(self._index_directory_async())

    def _request_exit(self) -> None:
        if not self._running:
            self.app.exit()
            return
        self._running = False
        self._save_if_needed('Сохранено перед выходом')
        if self._autosave_task and not self._autosave_task.done():
            self._autosave_task.cancel()
        self.app.exit()

    async def _autosave_loop(self) -> None:
        try:
            while self._running:
                await asyncio.sleep(self.AUTOSAVE_INTERVAL)
                self._save_if_needed('Автосохранено')
        except asyncio.CancelledError:
            pass

    def run(self) -> None:
        try:
            self.app.run()
        except KeyboardInterrupt:
            logger.info('Application interrupted by user')
        except Exception as exc:
            logger.error('Критическая ошибка приложения: %s', exc, exc_info=True)
        finally:
            self._running = False
            if self._autosave_task and not self._autosave_task.done():
                self._autosave_task.cancel()
            try:
                self._save_if_needed('Сохранено при выходе')
            except Exception as exc:  # noqa: BLE001
                logger.error('Не удалось сохранить при выходе: %s', exc, exc_info=True)
