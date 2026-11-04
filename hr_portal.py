# -*- coding: utf-8 -*-
"""Точка входа HR Portal. Запуск: python hr_portal.py (или собранный hr_portal.exe)."""

import sys


def main():
    try:
        from app.main_window import MainWindow
    except ImportError as ex:
        print("Ошибка импорта модулей приложения:", ex)
        print("Установите зависимости: pip install -r requirements.txt")
        sys.exit(1)
    try:
        app = MainWindow()
    except Exception as ex:  # например, нет дисплея/Tk
        print("Не удалось запустить графическое окно:", ex)
        sys.exit(2)
    app.mainloop()


if __name__ == "__main__":
    main()
