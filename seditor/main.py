"""
Точка входа приложения seditor
"""

from seditor.core.app import App


def main():
    """Главная функция приложения"""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
