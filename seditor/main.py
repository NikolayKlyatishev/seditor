"""
Точка входа приложения seditor
"""

import sys
from seditor.core.app_ptk import AppPTK


def main():
    """Главная функция приложения"""
    # Проверка, что запущено в терминале
    if not sys.stdin.isatty():
        print("Ошибка: seditor должен быть запущен в терминале (не через pipe/redirect).")
        print("Используйте: poetry run seditor")
        sys.exit(1)
    
    app = AppPTK()
    app.run()


if __name__ == "__main__":
    main()
