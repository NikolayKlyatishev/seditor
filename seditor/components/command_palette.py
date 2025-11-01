# -*- coding: utf-8 -*-
"""
Командная палитра для выбора команд и настроек
"""

from typing import Optional, Callable, List, Tuple
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document


class CommandPalette:
    """Командная палитра для быстрого доступа к командам"""
    
    # Доступные темы подсветки синтаксиса
    AVAILABLE_THEMES = [
        ('VS Code Dark+ (кастомная)', 'vscode-dark'),
        ('Monokai', 'monokai'),
        ('Dracula', 'dracula'),
        ('Nord', 'nord'),
        ('One Dark', 'one-dark'),
        ('Gruvbox Dark', 'gruvbox-dark'),
        ('Material', 'material'),
        ('Vim', 'vim'),
        ('Native', 'native'),
        ('Fruity', 'fruity'),
        ('Paraiso Dark', 'paraiso-dark'),
    ]
    
    def __init__(self):
        """Инициализация командной палитры"""
        self.buffer = Buffer(name='command_palette', multiline=False)
        self.is_visible = False
        self.selected_index = 0
        self.filtered_items: List[Tuple[str, str, Callable]] = []
        self.mode = 'command'  # 'command', 'theme_select', или 'search'
        self.search_results: List[Tuple[str, str, float]] = []  # Результаты поиска (path, name, score)
        
    def show(self) -> None:
        """Показать командную палитру"""
        self.is_visible = True
        self.buffer.text = ''
        self.selected_index = 0
        self.mode = 'command'
        self._update_filtered_items()
    
    def hide(self) -> None:
        """Скрыть командную палитру"""
        self.is_visible = False
        self.buffer.text = ''
        self.selected_index = 0
        self.filtered_items = []
    
    def toggle(self) -> None:
        """Переключить видимость"""
        if self.is_visible:
            self.hide()
        else:
            self.show()
    
    def _update_filtered_items(self) -> None:
        """Обновить список отфильтрованных команд"""
        query = self.buffer.text.lower()
        
        if self.mode == 'command':
            # Режим выбора команды
            all_commands = [
                ('Поиск файлов (Search)', 'search', lambda: self._enter_search()),
                ('Выбрать тему (Themes)', 'themes', lambda: self._enter_theme_select()),
                ('Переиндексировать (Reindex)', 'reindex', lambda: None),  # Будет обработано в app
                ('Сохранить файл (Save)', 'save', lambda: None),  # Будет обработано в app
                ('Выход (Quit)', 'quit', lambda: None),  # Будет обработано в app
            ]
            
            if query:
                self.filtered_items = [
                    (name, cmd, action) 
                    for name, cmd, action in all_commands 
                    if query in name.lower() or query in cmd.lower()
                ]
            else:
                self.filtered_items = all_commands
        
        elif self.mode == 'theme_select':
            # Режим выбора темы
            if query:
                self.filtered_items = [
                    (name, theme_id, lambda tid=theme_id: None)
                    for name, theme_id in self.AVAILABLE_THEMES
                    if query in name.lower() or query in theme_id.lower()
                ]
            else:
                self.filtered_items = [
                    (name, theme_id, lambda tid=theme_id: None)
                    for name, theme_id in self.AVAILABLE_THEMES
                ]
        
        elif self.mode == 'search':
            # Режим поиска файлов - результаты обновляются через set_search_results
            # Здесь просто форматируем существующие результаты
            self.filtered_items = [
                (f'{name} ({path})', path, lambda p=path: None)
                for path, name, score in self.search_results
            ]
        
        # Сбрасываем индекс если вышли за пределы
        if self.selected_index >= len(self.filtered_items):
            self.selected_index = max(0, len(self.filtered_items) - 1)
    
    def _enter_theme_select(self) -> None:
        """Войти в режим выбора темы"""
        self.mode = 'theme_select'
        self.buffer.text = ''
        self.selected_index = 0
        self._update_filtered_items()
    
    def _enter_search(self) -> None:
        """Войти в режим поиска файлов"""
        self.mode = 'search'
        self.buffer.text = ''
        self.selected_index = 0
        self.search_results = []
        self._update_filtered_items()
    
    def set_search_results(self, results: List[Tuple[str, str, float]]) -> None:
        """
        Установить результаты поиска
        
        Args:
            results: Список кортежей (path, name, score)
        """
        self.search_results = results
        self._update_filtered_items()
    
    def move_up(self) -> None:
        """Переместить выделение вверх"""
        if self.filtered_items:
            self.selected_index = max(0, self.selected_index - 1)
    
    def move_down(self) -> None:
        """Переместить выделение вниз"""
        if self.filtered_items:
            self.selected_index = min(len(self.filtered_items) - 1, self.selected_index + 1)
    
    def get_selected_command(self) -> Optional[str]:
        """Получить выбранную команду"""
        if self.filtered_items and 0 <= self.selected_index < len(self.filtered_items):
            return self.filtered_items[self.selected_index][1]
        return None
    
    def get_display_lines(self, max_lines: int = 10) -> List[Tuple[str, bool]]:
        """
        Получить строки для отображения
        
        Returns:
            Список кортежей (текст, выбран)
        """
        lines = []
        for idx, (name, cmd, _) in enumerate(self.filtered_items[:max_lines]):
            is_selected = (idx == self.selected_index)
            lines.append((name, is_selected))
        return lines
    
    def get_display_lines_with_paths(self, max_lines: int = 10) -> List[Tuple[str, str, bool]]:
        """
        Получить строки для отображения с разделением имени и пути (для режима поиска)
        
        Returns:
            Список кортежей (имя_файла, путь, выбран)
        """
        lines = []
        for idx, (path, name, score) in enumerate(self.search_results[:max_lines]):
            is_selected = (idx == self.selected_index)
            # Получаем относительный путь
            import os
            rel_path = path if not os.path.isabs(path) else os.path.relpath(path)
            lines.append((name, rel_path, is_selected))
        return lines
    
    def on_text_changed(self) -> None:
        """Обработчик изменения текста в поле ввода"""
        self._update_filtered_items()

