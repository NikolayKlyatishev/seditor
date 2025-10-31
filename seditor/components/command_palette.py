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
        self.mode = 'command'  # 'command' или 'theme_select'
        
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
                ('Выбрать тему (Themes)', 'themes', lambda: self._enter_theme_select()),
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
        
        # Сбрасываем индекс если вышли за пределы
        if self.selected_index >= len(self.filtered_items):
            self.selected_index = max(0, len(self.filtered_items) - 1)
    
    def _enter_theme_select(self) -> None:
        """Войти в режим выбора темы"""
        self.mode = 'theme_select'
        self.buffer.text = ''
        self.selected_index = 0
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
    
    def on_text_changed(self) -> None:
        """Обработчик изменения текста в поле ввода"""
        self._update_filtered_items()

