# -*- coding: utf-8 -*-
"""Главное окно приложения HR Portal."""

import os
import sys
import tkinter as tk
from tkinter import ttk

from app.database import Database
from app.seed import seed_if_empty
from app.services import HRService
from app.ui.common import style_app, info
from app.ui.employees import EmployeesFrame
from app.ui.reports import ReportsFrame


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HR Portal — управление персоналом организации")
        self.geometry("1200x760")
        self.minsize(940, 600)
        style_app(self)

        self.db = Database()
        seeded = seed_if_empty(self.db)
        self.service = HRService(self.db)

        # -------- верхняя панель --------
        header = ttk.Frame(self)
        header.pack(fill="x")
        brand = ttk.Frame(header, style="Card.TFrame")
        brand.pack(fill="x")
        ttk.Label(brand, text="🏢  HR Portal", style="H1.TLabel").pack(
            side="left", padx=16, pady=8)
        ttk.Label(brand, text="Кадровый учёт: приём • переводы • отпуска • "
                              "увольнения • пенсия",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(brand, text="Обновить данные",
                   command=self.refresh_all).pack(side="right", padx=16)

        # -------- вкладки --------
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(4, 0))

        self.employees_tab = EmployeesFrame(self.nb, self.service)
        self.nb.add(self.employees_tab, text="  Сотрудники  ")

        self.reports_tab = ReportsFrame(self.nb, self.service)
        self.nb.add(self.reports_tab, text="  Учёт кадров и отчёты  ")

        self._build_guide_tab()

        # -------- статусная строка --------
        self.status = ttk.Label(self, text="", style="Status.TLabel", anchor="w")
        self.status.pack(fill="x", side="bottom")

        self.bind("<<TabSelected>>", self._on_tab)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.employees_tab.show_list()
        self.reports_tab.refresh_all()
        if seeded and os.environ.get("HRPORTAL_HEADLESS") != "1":
            info(self, "Первый запуск",
                 "База данных создана и заполнена демонстрационными данными.\n"
                 "Все изменения сохраняются автоматически.")
        n = self.db.query_one(
            "SELECT COUNT(*) c FROM employees WHERE status='Работает'")["c"]
        self.set_status(f"Активных сотрудников: {n}   |   "
                        f"База: {self.db.path}")

    def _build_guide_tab(self):
        fr = ttk.Frame(self.nb, style="Card.TFrame", padding=18)
        self.nb.add(fr, text="  Справка  ")
        text = tk.Text(fr, wrap="word", bg="#ffffff", relief="flat",
                       font=("Segoe UI", 11), padx=16, pady=12)
        text.pack(fill="both", expand=True)
        guide = """\nКак вести кадровый учёт в HR Portal\n
1. ПРИЁМ НА РАБОТУ
   Вкладка «Сотрудники» → кнопка «+ Принять на работу».
   Заполните ФИО, даты, должность, оклад, тип занятости (постоянный, срочный
   договор, испытательный срок, совместительство, стажёр), паспортные данные,
   СНИЛС и ИНН. Кадровая запись о приёме создаётся автоматически.

2. РАБОТА СОТРУДНИКА
   Двойной клик по строке открывает карточку сотрудника со всеми вкладками:
   события, отпуска, больничные, командировки, дисциплина, обучение,
   история изменений должности/оклада.

3. ПЕРЕВОДЫ И ПОВЫШЕНИЯ
   В карточке: «Перевод / повышение» — смена должности, подразделения,
   оклада с указанием основания и даты. Все изменения пишутся в историю.

4. ОТПУСКА, БОЛЬНИЧНЫЕ, КОМАНДИРОВКИ
   Кнопки в карточке оформляют соответствующие записи; ежегодный оплачиваемый
   отпуск ограничен 28 календарными днями (ТК РФ ст. 115).

5. ДИСЦИПЛИНА И ОБУЧЕНИЕ
   Взыскания (замечание, выговор), поощрения (премия, благодарность),
   программы повышения квалификации с результатом обучения.

6. УВОЛЬНЕНИЕ И ВЫХОД НА ПЕНСИЮ
   «Увольнение / пенсия» — причина по классификации ТК РФ, основание
   (статья/приказ), дата. При достижении пенсионного возраста программа
   подсказывает выбрать «Выход на пенсию»; сотрудник получает статус
   «На пенсии» и заносится в архив выбывших.

7. УЧЁТ КАДРОВ И ОТЧЁТЫ
   Вкладка «Учёт кадров и отчёты»: сводка по численности и ФОТ, отчёт о
   движении кадров за период, штатное расписание (с поиском вакансий),
   график отпусков, предпенсионный резерв, архив уволенных с возможностью
   возврата на работу. Любой отчёт можно выгрузить в XLSX/CSV.

Хранение: база SQLite находится в папке пользователя (Windows: %APPDATA%\\HRPortal).
Резервная копия = скопировать файл hr_portal.db.\n"""
        text.insert("1.0", guide)
        text.config(state="disabled")

    def refresh_all(self):
        self.employees_tab.refresh()
        self.reports_tab.refresh_all()
        self.set_status("Данные обновлены из базы.")

    def _on_tab(self, *_):
        idx = self.nb.index(self.nb.select())
        if idx == 1:
            self.reports_tab.refresh_all()

    def set_status(self, msg):
        self.status.config(text=msg)

    def _on_close(self):
        self.db.close()
        self.destroy()

    def run_smoke_check(self, callback):
        """Автопроверка интерфейса (используется в тестах и при запуске с флагом --smoke)."""
        def drive():
            try:
                for i in range(len(self.nb.tabs())):
                    self.nb.select(i)
                    self.update()
                emp = self.employees_tab
                rows = emp.tree.get_children()
                assert rows, "Список сотрудников пуст"
                emp.show_card(int(rows[0]))
                self.update()
                assert emp.card_title.cget("text"), "Пустой заголовок карточки"
                assert emp.nb.tabs(), "Нет вкладок записей"
                assert emp.record_trees["events"].get_children(), \
                    "Нет кадровых событий у сотрудника"
                emp.show_list()
                self.update()
                self.reports_tab.build_movement()
                self.update()
                assert self.reports_tab.mv_tree.get_children(), \
                    "Пустой отчёт о движении кадров"
                assert self.reports_tab.pr_tree.get_children(), \
                    "Пустой список предпенсионного резерва"
                assert self.reports_tab.ar_tree.get_children(), \
                    "Пустой архив уволенных"
                result = ("PASS", None)
            except Exception as ex:
                result = ("FAIL", str(ex))
            finally:
                self.db.close()
                try:
                    self.destroy()
                except Exception:
                    pass
                callback(*result)
        # закрываем возможные модальные окна приветствия и стартуем проверку
        self.after(400, drive)


def run_smoke():
    """Немодальная проверка интерфейса без mainloop (для тестов/CI)."""
    app = MainWindow()
    outcome = {"status": None, "error": None}

    def drive():
        try:
            for i in range(len(app.nb.tabs())):
                app.nb.select(i)
                app.update_idletasks()
                app.update()
            emp = app.employees_tab
            rows = emp.tree.get_children()
            assert rows, "Список сотрудников пуст"
            emp.show_card(int(rows[0]))
            app.update()
            assert emp.card_title.cget("text"), "Пустой заголовок карточки"
            assert emp.nb.tabs(), "Нет вкладок записей"
            assert emp.record_trees["events"].get_children(), \
                "Нет кадровых событий у сотрудника"
            emp.show_list()
            app.update()
            app.reports_tab.build_movement()
            app.update()
            assert app.reports_tab.mv_tree.get_children(), \
                "Пустой отчёт о движении кадров"
            assert app.reports_tab.pr_tree.get_children(), \
                "Пустой список предпенсионного резерва"
            assert app.reports_tab.ar_tree.get_children(), \
                "Пустой архив уволенных"
            outcome["status"] = "PASS"
        except Exception as ex:
            outcome["status"] = "FAIL"
            outcome["error"] = str(ex)
        finally:
            app.db.close()
            try:
                app.destroy()
            except Exception:
                pass

    deadline = time.time() + 25
    app.update()
    while outcome["status"] is None and time.time() < deadline:
        app.update_idletasks()
        app.update()
        time.sleep(0.03)
        if not drive in getattr(app, "_after_callbacks", lambda *_: [])():
            # планируем проверку один раз через after
            pass
    if outcome["status"] is None:
        drive()
    return outcome["status"], outcome["error"]


def main():
    smoke = "--smoke" in sys.argv
    app = MainWindow()
    if smoke:
        def done(status, err):
            print(f"SMOKE {status}" + (f": {err}" if err else ""))
            sys.exit(0 if status == "PASS" else 3)
        app.run_smoke_check(done)
    app.mainloop()


if __name__ == "__main__":
    main()
