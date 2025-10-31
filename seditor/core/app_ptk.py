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
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import DynamicLexer

from seditor.terminal.layout import Layout as ScreenLayout
from seditor.components.editor_ptk import EditorPanePTK
from seditor.components.file_tree import FileTreePane

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

        self.focused_pane: str = 'tree'
        self.current_file: Optional[str] = None
        self._status_message: str = ''
        self._autosave_task: Optional[asyncio.Task] = None
        self._running: bool = False

        self.kb = KeyBindings()
        self._setup_keybindings()

        self.tree_control = FormattedTextControl(
            text=self._get_tree_content,
            focusable=True,
            show_cursor=False,
        )
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

        body = VSplit(
            [self.tree_window, self.separator_window, self.editor_window],
            padding=0,
        )
        container = HSplit([body, self.status_window])

        self.layout = PTKLayout(container, focused_element=self.tree_window)
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            style=self._create_style(),
            refresh_interval=0.5,
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
        return Style(
            [
                ('tree', 'bg:#1e1e1e fg:#d4d4d4'),
                ('tree.header', 'fg:#888'),
                ('tree.text', 'fg:#d4d4d4'),
                ('tree.selected', 'fg:#d4d4d4'),
                ('tree.selected.focused', 'bg:#3a3d41 fg:#ffffff'),
                ('tree.empty', 'fg:#666'),
                ('separator', 'fg:#444'),
                ('editor', 'bg:#1e1e1e fg:#d4d4d4'),
                ('editor.line-number', '#858585'),
                ('editor.cursor', 'bg:#aeafad'),
                ('editor.selection', 'bg:#264f78'),
                ('status', 'bg:#1b1b1b fg:#d4d4d4'),
                ('status.label', 'bold'),
                ('status.separator', 'fg:#555'),
                ('status.message', 'fg:#9cdcfe'),
            ]
        )

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

    def _setup_keybindings(self) -> None:
        @self.kb.add('tab')
        def _(event) -> None:
            self._toggle_focus()

        @self.kb.add('q')
        def _(event) -> None:
            self._request_exit()

        tree_focus = Condition(lambda: self.focused_pane == 'tree')
        editor_focus = Condition(lambda: self.focused_pane == 'editor')

        @self.kb.add('enter', filter=tree_focus)
        def _(event) -> None:
            result = self.file_tree_pane.enter()
            if result:
                self._open_file(result)
            else:
                self._set_status(
                    os.path.basename(self.file_tree_pane.tree.current_path) or self.file_tree_pane.tree.current_path
                )

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

        @self.kb.add('escape', 'b', filter=editor_focus)
        def _(event) -> None:
            buffer = event.app.current_buffer
            buffer.start_of_word()

        @self.kb.add('escape', 'f', filter=editor_focus)
        def _(event) -> None:
            buffer = event.app.current_buffer
            buffer.end_of_word()

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
