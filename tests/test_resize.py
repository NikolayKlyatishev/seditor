# -*- coding: utf-8 -*-
"""
Тесты для проверки обработки изменения размеров терминала
"""

import pytest
from seditor.terminal.manager import TerminalManager
from seditor.core.app import App


def test_terminal_manager_has_size_changed():
    """Тест проверки изменения размеров терминала"""
    tm = TerminalManager()
    initial_width = tm.width
    initial_height = tm.height
    
    # Сразу после инициализации размеры не должны измениться
    assert tm.has_size_changed() is False
    
    # Обновляем размеры терминала
    tm.refresh_size()
    # После refresh_size размеры не должны быть изменены (если терминал не изменился)
    assert tm.has_size_changed() is False


def test_app_refresh_updates_layout():
    """Тест обновления layout при вызове refresh"""
    app = App()
    initial_tree_width = app.layout.tree_width
    initial_editor_width = app.layout.editor_width
    
    # Обновляем размеры терминала
    # В тестах размеры терминала не изменяются, но refresh должен обновить layout
    app.refresh()
    
    # После refresh размеры должны быть обновлены
    assert app.layout.tree_width >= 0
    assert app.layout.editor_width >= 0
    # Размеры могут измениться или остаться теми же после refresh


def test_app_has_resize_detection():
    """Тест проверки наличия механизма определения изменения размеров терминала в App"""
    app = App()
    
    # Проверяем, что у терминального менеджера есть метод has_size_changed
    assert hasattr(app.term_manager, 'has_size_changed')
    
    # Проверяем, что метод возвращает булево значение
    result = app.term_manager.has_size_changed()
    assert isinstance(result, bool)
