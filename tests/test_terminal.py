# -*- coding: utf-8 -*-
"""
Тесты для терминального менеджера и разметки
"""

import pytest
from seditor.terminal.manager import TerminalManager
from seditor.terminal.layout import Layout


def test_terminal_manager_initialization():
    """Тест инициализации TerminalManager"""
    tm = TerminalManager()
    assert tm.width > 0
    assert tm.height > 0


def test_terminal_manager_get_size():
    """Тест получения размеров терминала"""
    tm = TerminalManager()
    width, height = tm.get_size()
    assert width > 0
    assert height > 0
    assert width == tm.width
    assert height == tm.height


def test_layout_initialization():
    """Тест инициализации Layout"""
    layout = Layout(100, 30)
    assert layout.tree_width == 25  # 25% от 100
    assert layout.editor_width == 74  # 100 - 25 - 1 (разделитель)
    assert layout.separator_x == 25
    assert layout.height == 30


def test_layout_panes():
    """Тест получения размеров панелей"""
    layout = Layout(100, 30)
    panes = layout.get_panes()
    assert panes.tree_width == 25
    assert panes.editor_width == 74
    assert panes.separator_x == 25
    assert panes.height == 30


def test_layout_bounds():
    """Тест получения границ панелей"""
    layout = Layout(100, 30)
    
    tree_bounds = layout.get_tree_bounds()
    assert tree_bounds == (0, 0, 25, 30)
    
    editor_bounds = layout.get_editor_bounds()
    assert editor_bounds == (26, 0, 74, 30)  # separator_x + 1


def test_layout_update_size():
    """Тест обновления размеров layout"""
    layout = Layout(100, 30)
    layout.update_size(200, 40)
    
    assert layout.tree_width == 50  # 25% от 200
    assert layout.editor_width == 149  # 200 - 50 - 1
    assert layout.separator_x == 50
    assert layout.height == 40


def test_layout_proportions():
    """Тест проверки пропорций 25/75"""
    layout = Layout(100, 30)
    
    # Проверяем, что tree_width составляет 25%
    tree_percent = (layout.tree_width / layout.terminal_width) * 100
    assert 24 <= tree_percent <= 26  # Погрешность на округление
    
    # Проверяем, что editor_width составляет 75%
    editor_percent = (layout.editor_width / layout.terminal_width) * 100
    assert 73 <= editor_percent <= 75  # Погрешность на разделитель
