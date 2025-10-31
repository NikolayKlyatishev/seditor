# -*- coding: utf-8 -*-
"""
Тесты для командной палитры
"""

from seditor.components.command_palette import CommandPalette


def test_command_palette_init():
    """Тест инициализации командной палитры"""
    palette = CommandPalette()
    assert not palette.is_visible
    assert palette.mode == 'command'
    assert palette.selected_index == 0


def test_command_palette_show_hide():
    """Тест показа/скрытия командной палитры"""
    palette = CommandPalette()
    
    palette.show()
    assert palette.is_visible
    assert palette.mode == 'command'
    assert len(palette.filtered_items) > 0
    
    palette.hide()
    assert not palette.is_visible


def test_command_palette_navigation():
    """Тест навигации в командной палитре"""
    palette = CommandPalette()
    palette.show()
    
    initial_index = palette.selected_index
    palette.move_down()
    assert palette.selected_index == initial_index + 1
    
    palette.move_up()
    assert palette.selected_index == initial_index


def test_command_palette_theme_select():
    """Тест выбора темы"""
    palette = CommandPalette()
    palette.show()
    
    # Переходим в режим выбора темы
    palette._enter_theme_select()
    assert palette.mode == 'theme_select'
    assert len(palette.filtered_items) == len(CommandPalette.AVAILABLE_THEMES)


def test_command_palette_filter():
    """Тест фильтрации команд"""
    palette = CommandPalette()
    palette.show()
    
    # Фильтруем по "theme"
    palette.buffer.text = 'theme'
    palette.on_text_changed()
    
    # Должна остаться только команда с "theme"
    assert len(palette.filtered_items) > 0
    assert any('theme' in item[0].lower() for item in palette.filtered_items)


def test_command_palette_get_selected():
    """Тест получения выбранной команды"""
    palette = CommandPalette()
    palette.show()
    
    selected = palette.get_selected_command()
    assert selected is not None
    assert isinstance(selected, str)

