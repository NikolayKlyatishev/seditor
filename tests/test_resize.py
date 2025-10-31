# -*- coding: utf-8 -*-
"""
Тесты для проверки обработки изменения размеров терминала
"""

from seditor.terminal.manager import TerminalManager
from seditor.core.app_ptk import AppPTK
from seditor.components.editor_ptk import EditorPanePTK
from seditor.terminal.layout import Layout as ScreenLayout


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


def test_editor_ptk_dirty_flag(tmp_path):
    """Проверяем флаг изменённости текста в EditorPanePTK."""
    layout = ScreenLayout(80, 24)
    editor = EditorPanePTK(layout)
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")

    assert editor.load_file(str(file_path))
    assert editor.has_unsaved_changes() is False

    editor.buffer.cursor_position = len(editor.buffer.text)
    editor.buffer.insert_text(" world")
    assert editor.has_unsaved_changes() is True

    assert editor.save_file() is True
    assert editor.has_unsaved_changes() is False
    assert file_path.read_text(encoding="utf-8") == "hello world"


def test_app_ptk_save_if_needed(tmp_path):
    """Проверяем автосохранение через _save_if_needed."""
    app = AppPTK()
    temp_file = tmp_path / "auto.txt"
    temp_file.write_text("data", encoding="utf-8")

    # Без открытого файла сохранение не требуется
    assert app._save_if_needed('test') is False

    # Загружаем файл, изменений нет
    assert app.editor_pane.load_file(str(temp_file))
    assert app._save_if_needed('test') is False

    # Вносим изменения и проверяем, что файл обновлён
    app.editor_pane.buffer.cursor_position = len(app.editor_pane.buffer.text)
    app.editor_pane.buffer.insert_text('!')
    assert app._save_if_needed('test') is True
    assert temp_file.read_text(encoding="utf-8").endswith('!')
