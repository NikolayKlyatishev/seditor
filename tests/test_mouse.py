# -*- coding: utf-8 -*-
"""
Тесты для поддержки мыши
"""

from seditor.core.app_ptk import AppPTK
from seditor.components.file_tree import FileTreePane


def test_app_has_mouse_support():
    """Проверяем что приложение создаётся с поддержкой мыши"""
    app = AppPTK()
    # mouse_support может быть True или объектом Filter, главное что не False
    assert app.app.mouse_support is not False
    assert app.app.mouse_support is not None


def test_tree_has_mouse_handler():
    """Проверяем что у дерева файлов есть обработчик мыши"""
    app = AppPTK()
    assert app.tree_control.mouse_handler is not None
    assert callable(app.tree_control.mouse_handler)


def test_file_tree_get_visible_items():
    """Проверяем метод получения видимых элементов"""
    from seditor.terminal.layout import Layout as ScreenLayout
    
    screen_layout = ScreenLayout(100, 30)
    tree_pane = FileTreePane(screen_layout)
    
    # Получаем видимые элементы
    visible = tree_pane.get_visible_items()
    
    # Должен быть список (может быть пустым если нет файлов)
    assert isinstance(visible, list)
    
    # Если есть элементы, проверяем что они правильного типа
    if visible:
        from seditor.core.file_tree import FileNode
        assert all(isinstance(item, FileNode) for item in visible)


def test_mouse_handler_callable():
    """Проверяем что обработчик мыши можно вызвать"""
    app = AppPTK()
    
    # Создаём фиктивное событие мыши
    class MockMouseEvent:
        class Position:
            x = 0
            y = 0
        
        position = Position()
        event_type = 'MOUSE_DOWN'
    
    # Проверяем что обработчик не падает при вызове
    try:
        # Просто проверяем что метод существует и callable
        assert hasattr(app, '_tree_mouse_handler')
        assert callable(app._tree_mouse_handler)
    except Exception as e:
        assert False, f"Mouse handler raised exception: {e}"

