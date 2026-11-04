# -*- coding: utf-8 -*-
"""Вкладка «Учёт кадров»: сводка, движение, штатное расписание,
графики отпусков, пенсионный резерв, архив уволенных."""

import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog

from app.services import HRService, full_name, pretty
from app.ui.common import ask_form, error, info


def _card(parent, title):
    fr = ttk.Frame(parent, style="Card.TFrame", padding=(14, 10),
                   relief="solid", borderwidth=1)
    head = ttk.Label(fr, text=title, style="H1.TLabel")
    head.pack(anchor="w")
    body = ttk.Frame(fr, style="Card.TFrame")
    body.pack(fill="both", expand=True, pady=(6, 0))
    return fr, body


class ReportsFrame(ttk.Frame):
    def __init__(self, master, service: HRService):
        super().__init__(master)
        self.service = service
        self._build()

    def _build(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        self.nb = ttk.Notebook(wrap)
        self.nb.pack(fill="both", expand=True)
        for title, fn in [
            ("Сводка", self._tab_summary),
            ("Движение кадров", self._tab_movement),
            ("Штатное расписание", self._tab_staffing),
            ("График отпусков", self._tab_vacation_plan),
            ("Пенсии и увольнения", self._tab_pension),
            ("Архив", self._tab_archive),
        ]:
            page = ttk.Frame(self.nb, style="Card.TFrame", padding=10)
            self.nb.add(page, text=title)
            fn(page)

    # ---------------- Сводка ----------------
    def _tab_summary(self, page):
        row = ttk.Frame(page, style="Card.TFrame")
        row.pack(fill="x")
        self.stat_cards = {}
        for key, label in [("works", "Работают"), ("fired", "Уволены"),
                           ("pension", "На пенсии"), ("hired_y", "Принято за год"),
                           ("left_y", "Выбыло за год"), ("avg", "Средний оклад"),
                           ("payroll", "ФОТ в месяц")]:
            c, b = _card(row, label)
            c.pack(side="left", padx=(0, 10), fill="y")
            lbl = ttk.Label(b, text="—", font=("Segoe UI", 18, "bold"))
            lbl.pack()
            self.stat_cards[key] = lbl
        page.columnconfigure(0, weight=1)

        bottom = ttk.Frame(page, style="Card.TFrame")
        bottom.pack(fill="both", expand=True, pady=(12, 0))
        left, lb = _card(bottom, "Численность по подразделениям")
        left.pack(side="left", fill="both", expand=True)
        self.dept_tree = ttk.Treeview(lb, columns=("dept", "cnt"),
                                      show="headings", height=9)
        self.dept_tree.heading("dept", text="Подразделение")
        self.dept_tree.heading("cnt", text="Чел.")
        self.dept_tree.column("dept", width=260)
        self.dept_tree.column("cnt", width=70, anchor="e")
        self.dept_tree.pack(fill="both", expand=True)
        right, rb = _card(bottom, "Кадровые события")
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.ev_tree = ttk.Treeview(rb, columns=("ev", "cnt"),
                                    show="headings", height=9)
        self.ev_tree.heading("ev", text="Событие")
        self.ev_tree.heading("cnt", text="Кол-во")
        self.ev_tree.column("ev", width=220)
        self.ev_tree.column("cnt", width=70, anchor="e")
        self.ev_tree.pack(fill="both", expand=True)

    def refresh_summary(self):
        s = self.service.stats()
        by_status = {r["status"]: r["c"] for r in s["by_status"]}
        year_ago = (date.today() - timedelta(days=365)).isoformat()
        hired = self.service.db.query_one(
            "SELECT COUNT(*) c FROM events WHERE event_type='Приём на работу' "
            "AND event_date>=?", (year_ago,))["c"]
        left = self.service.db.query_one(
            "SELECT COUNT(*) c FROM events WHERE event_type IN "
            "('Увольнение','Уход на пенсию') AND event_date>=?",
            (year_ago,))["c"]
        vals = {
            "works": by_status.get("Работает", 0),
            "fired": by_status.get("Уволен", 0),
            "pension": by_status.get("На пенсии", 0),
            "hired_y": hired,
            "left_y": left,
            "avg": f"{s['avg_salary']:,.0f}".replace(",", " ") + " ₽",
            "payroll": f"{s['payroll']:,.0f}".replace(",", " ") + " ₽",
        }
        for k, v in vals.items():
            self.stat_cards[k].config(text=str(v))
        self.dept_tree.delete(*self.dept_tree.get_children())
        for r in s["by_department"]:
            self.dept_tree.insert("", "end", values=(r["name"], r["c"]))
        self.ev_tree.delete(*self.ev_tree.get_children())
        for r in s["by_event"]:
            self.ev_tree.insert("", "end", values=(r["event_type"], r["c"]))

    # ---------------- Движение ----------------
    def _tab_movement(self, page):
        top = ttk.Frame(page, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Отчёт о движении кадров за период:",
                  style="Card.TLabel").pack(side="left")
        self.mv_from = tk.StringVar(value=(date.today().replace(month=1, day=1)
                                           .strftime("%d.%m.%Y")))
        self.mv_to = tk.StringVar(value=date.today().strftime("%d.%m.%Y"))
        e1 = ttk.Entry(top, textvariable=self.mv_from, width=12)
        e1.pack(side="left", padx=(8, 4))
        ttk.Label(top, text="—", style="Card.TLabel").pack(side="left")
        e2 = ttk.Entry(top, textvariable=self.mv_to, width=12)
        e2.pack(side="left", padx=(0, 8))
        ttk.Button(top, text="Построить", style="Accent.TButton",
                   command=self.build_movement).pack(side="left")
        ttk.Button(top, text="Экспорт XLSX",
                   command=lambda: self._export_xlsx("movement")).pack(
            side="right")

        cols = ("metric", "value")
        self.mv_tree = ttk.Treeview(page, columns=cols, show="headings",
                                    height=14)
        self.mv_tree.heading("metric", text="Показатель")
        self.mv_tree.heading("value", text="Значение")
        self.mv_tree.column("metric", width=380)
        self.mv_tree.column("value", width=140, anchor="e")
        self.mv_tree.pack(fill="both", expand=True, pady=8)
        self._movement_rows = []

    def build_movement(self):
        try:
            from app.services import parse_date
            d1, d2 = parse_date(self.mv_from.get()), parse_date(self.mv_to.get())
            if d2 < d1:
                raise ValueError("Начало периода позже конца.")
        except ValueError as ex:
            error(self, "Период", str(ex))
            return
        i1, i2 = d1.isoformat(), d2.isoformat()
        q = lambda sql, p: self.service.db.query_one(sql, p)["c"]
        hired = q("SELECT COUNT(*) c FROM events WHERE event_type='Приём на работу' "
                  "AND event_date BETWEEN ? AND ?", (i1, i2))
        fired = q("SELECT COUNT(*) c FROM terminations WHERE pension=0 "
                  "AND term_date BETWEEN ? AND ?", (i1, i2))
        retired = q("SELECT COUNT(*) c FROM terminations WHERE pension=1 "
                    "AND term_date BETWEEN ? AND ?", (i1, i2))
        transfers = q("SELECT COUNT(*) c FROM events WHERE event_type LIKE 'Перевод%' "
                      "AND event_date BETWEEN ? AND ?", (i1, i2))
        promotions = q("SELECT COUNT(*) c FROM events WHERE event_type='Повышение' "
                      "AND event_date BETWEEN ? AND ?", (i1, i2))
        vacations = q("SELECT COUNT(*) c FROM vacations WHERE start_date BETWEEN ? AND ?",
                      (i1, i2))
        sick_days = self.service.db.query_one(
            "SELECT COALESCE(SUM(julianday(end_date)-julianday(start_date)+1),0) s "
            "FROM sick_leaves WHERE start_date BETWEEN ? AND ?", (i1, i2))["s"]
        trips = q("SELECT COUNT(*) c FROM business_trips WHERE start_date "
                  "BETWEEN ? AND ?", (i1, i2))
        active_now = q("SELECT COUNT(*) c FROM employees WHERE status='Работает'", ())
        left_total = fired + retired
        retention = (100.0 * (active_now - left_total) / active_now
                     if active_now else 0)
        rows = [
            ("Принято на работу", hired),
            ("Уволено", fired),
            ("Ушло на пенсию", retired),
            ("Переведено", transfers),
            ("Повышено", promotions),
            ("Отпусков начато", vacations),
            ("Дней больничных", int(sick_days)),
            ("Командировок", trips),
            ("Работают сейчас", active_now),
            (f"Коэффициент сохранности кадров", f"{retention:.1f} %"),
        ]
        self._movement_rows = rows
        self.mv_tree.delete(*self.mv_tree.get_children())
        for m, v in rows:
            self.mv_tree.insert("", "end", values=(m, v))

    # ---------------- Штатное расписание ----------------
    def _tab_staffing(self, page):
        top = ttk.Frame(page, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Button(top, text="+ Добавить должность", style="Accent.TButton",
                   command=self.add_position).pack(side="left")
        ttk.Button(top, text="Экспорт XLSX",
                   command=lambda: self._export_xlsx("staffing")).pack(
            side="right", padx=(0, 8))
        cols = ("pos", "dept", "base", "filled", "free_note")
        heads = ("Должность", "Подразделение", "Базовый оклад",
                 "Занято чел.", "Комментарий")
        self.st_tree = ttk.Treeview(page, columns=cols, show="headings",
                                    height=14)
        for c, h in zip(cols, heads):
            self.st_tree.heading(c, text=h)
            self.st_tree.column(c, width={"pos": 220, "dept": 170, "base": 120,
                                          "filled": 90, "free_note": 200}[c],
                                anchor="w")
        self.st_tree.pack(fill="both", expand=True, pady=8)
        self._staffing_rows = []

    def refresh_staffing(self):
        self.st_tree.delete(*self.st_tree.get_children())
        self._staffing_rows = []
        rows = self.service.db.query(
            "SELECT p.title, d.name dept, p.base_salary, "
            "(SELECT COUNT(*) FROM employees e WHERE e.position_id=p.id "
            " AND e.status='Работает') filled "
            "FROM positions p LEFT JOIN departments d ON d.id=p.department_id "
            "ORDER BY d.name, p.title")
        for r in rows:
            note = "вакансия!" if r["filled"] == 0 else ""
            self.st_tree.insert("", "end", values=(
                r["title"], r["dept"] or "—",
                f"{r['base_salary']:,.0f}".replace(",", " "),
                r["filled"], note))
            self._staffing_rows.append((r["title"], r["dept"] or "",
                                        r["base_salary"], r["filled"], note))

    def add_position(self):
        deps = [d["name"] for d in self.service.list_departments()]
        dep_map = {d["name"]: d["id"] for d in self.service.list_departments()}
        v = ask_form(self, "Новая должность", [
            {"key": "title", "label": "Название", "value": ""},
            {"key": "dep", "label": "Подразделение", "kind": "combo",
             "options": deps, "value": deps[0] if deps else ""},
            {"key": "salary", "label": "Базовый оклад, ₽", "value": "0"},
        ])
        if not v:
            return
        try:
            self.service.add_position(v["title"], dep_map.get(v["dep"]),
                                      v["salary"])
        except Exception as ex:
            error(self, "Ошибка", str(ex))
            return
        self.refresh_staffing()

    # ---------------- График отпусков ----------------
    def _tab_vacation_plan(self, page):
        top = ttk.Frame(page, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="График отпусков (текущий год):",
                  style="H1.TLabel").pack(side="left")
        ttk.Button(top, text="Экспорт XLSX",
                   command=lambda: self._export_xlsx("vacations")).pack(side="right")
        self.year_lbl = ttk.Label(top, text="", style="Muted.TLabel")
        self.year_lbl.pack(side="right", padx=10)
        cols = ("month", "fio", "position", "type", "period", "days", "status")
        heads = ("Месяц", "ФИО", "Должность", "Вид отпуска", "Период",
                 "Дней", "Статус")
        self.vp_tree = ttk.Treeview(page, columns=cols, show="headings",
                                    height=14)
        widths = dict(zip(cols, (70, 220, 170, 190, 170, 60, 110)))
        for c, h in zip(cols, heads):
            self.vp_tree.heading(c, text=h)
            self.vp_tree.column(c, width=widths[c])
        self.vp_tree.pack(fill="both", expand=True, pady=8)
        self._vp_rows = []

    MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль",
              "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

    def refresh_vacation_plan(self):
        year = date.today().year
        self.year_lbl.config(text=f"год {year}")
        rows = self.service.db.query(
            "SELECT v.*, e.last_name, e.first_name, e.middle_name, "
            "p.title pos FROM vacations v "
            "JOIN employees e ON e.id=v.employee_id "
            "LEFT JOIN positions p ON p.id=e.position_id "
            "WHERE substr(v.start_date,1,4)=? ORDER BY v.start_date", (str(year),))
        self.vp_tree.delete(*self.vp_tree.get_children())
        self._vp_rows = []
        for r in rows:
            m = int(r["start_date"][5:7]) - 1
            days = (date.fromisoformat(r["end_date"]) -
                    date.fromisoformat(r["start_date"])).days + 1
            fio = full_name(r)
            vals = (self.MONTHS[m], fio, r["pos"] or "—", r["vtype"],
                    f"{pretty(r['start_date'])} – {pretty(r['end_date'])}",
                    days, r["status"])
            self.vp_tree.insert("", "end", values=vals)
            self._vp_rows.append(vals)

    # ---------------- Пенсии и увольнения ----------------
    def _tab_pension(self, page):
        intro = ttk.Label(
            page, style="Card.TLabel", justify="left",
            text=("Кандидаты на ближайший выход на пенсию (возраст на пороге) "
                  "и список выбывших сотрудников.\n"
                  "Порог учёта: предпенсионный интервал ±3 года."))
        intro.pack(anchor="w", pady=(0, 8))
        cols = ("fio", "age", "birth", "position", "dept", "tenure", "advice")
        heads = ("ФИО", "Возраст", "Дата рождения", "Должность",
                 "Подразделение", "Стаж", "Рекомендация")
        self.pr_tree = ttk.Treeview(page, columns=cols, show="headings",
                                    height=9)
        widths = dict(zip(cols, (210, 70, 110, 170, 150, 90, 230)))
        for c, h in zip(cols, heads):
            self.pr_tree.heading(c, text=h)
            self.pr_tree.column(c, width=widths[c])
        self.pr_tree.pack(fill="both", expand=True)
        self.pr_tree.tag_configure("soon", foreground="#b23b3b")

        ttk.Separator(page, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(page, text="Выбытия (архив увольнений):",
                  style="H1.TLabel").pack(anchor="w")
        cols2 = ("fio", "date", "reason", "basis", "kind")
        heads2 = ("ФИО", "Дата", "Причина", "Основание", "Вид")
        self.tr_tree = ttk.Treeview(page, columns=cols2, show="headings",
                                    height=7)
        widths2 = dict(zip(cols2, (210, 100, 220, 170, 110)))
        for c, h in zip(cols2, heads2):
            self.tr_tree.heading(c, text=h)
            self.tr_tree.column(c, width=widths2[c])
        self.tr_tree.pack(fill="both", expand=True)
        self.tr_tree.tag_configure("pen", foreground="#8a5fb0")

    def refresh_pension(self):
        self.pr_tree.delete(*self.pr_tree.get_children())
        for e, age in self.service.upcoming_retirements():
            yrs = self.service.tenure_days(e) // 365
            advice = ("Готовиться к оформлению пенсии" if age >= 61 else
                      "Запланировать замену позиции" if age >= 58 else
                      "Мониторинг")
            tag = ("soon",) if age >= 61 else ()
            self.pr_tree.insert("", "end", tags=tag, values=(
                full_name(e), age, pretty(e["birth_date"]),
                e.get("position_title") or "—",
                e.get("department_name") or "—", f"{yrs} лет", advice))
        self.tr_tree.delete(*self.tr_tree.get_children())
        rows = self.service.db.query(
            "SELECT t.*, e.last_name, e.first_name, e.middle_name "
            "FROM terminations t JOIN employees e ON e.id=t.employee_id "
            "ORDER BY t.term_date DESC")
        for r in rows:
            kind = "Пенсия" if r["pension"] else "Увольнение"
            tag = ("pen",) if r["pension"] else ()
            self.tr_tree.insert("", "end", tags=tag, values=(
                full_name(r), pretty(r["term_date"]), r["reason"],
                r["basis"] or "—", kind))

    # ---------------- Архив ----------------
    def _tab_archive(self, page):
        top = ttk.Frame(page, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Архив уволенных и пенсионеров:",
                  style="H1.TLabel").pack(side="left")
        ttk.Button(top, text="Вернуть на работу…",
                   command=self.reinstate_selected).pack(side="right")
        cols = ("fio", "position", "dept", "hire", "last", "status")
        heads = ("ФИО", "Последняя должность", "Подразделение",
                 "Приём", "Последнее событие", "Статус")
        self.ar_tree = ttk.Treeview(page, columns=cols, show="headings",
                                    height=15)
        widths = dict(zip(cols, (220, 190, 160, 100, 130, 100)))
        for c, h in zip(cols, heads):
            self.ar_tree.heading(c, text=h)
            self.ar_tree.column(c, width=widths[c])
        self.ar_tree.pack(fill="both", expand=True, pady=8)

    def refresh_archive(self):
        self.ar_tree.delete(*self.ar_tree.get_children())
        rows = self.service.db.query(
            "SELECT e.*, p.title pos, d.name dept FROM employees e "
            "LEFT JOIN positions p ON p.id=e.position_id "
            "LEFT JOIN departments d ON d.id=e.department_id "
            "WHERE e.status IN ('Уволен','На пенсии') ORDER BY e.last_name")
        for r in rows:
            last = self.service.db.query_one(
                "SELECT event_date FROM events WHERE employee_id=? "
                "AND event_type IN ('Увольнение','Уход на пенсию') "
                "ORDER BY event_date DESC LIMIT 1", (r["id"],))
            self.ar_tree.insert("", "end", iid=str(r["id"]), values=(
                full_name(r), r["pos"] or "—", r["dept"] or "—",
                pretty(r["hire_date"]),
                pretty(last["event_date"]) if last else "—", r["status"]))

    def reinstate_selected(self):
        sel = self.ar_tree.selection()
        if not sel:
            error(self, "Архив", "Выберите сотрудника в списке.")
            return
        eid = int(sel[0])
        positions = [p["title"] for p in self.service.list_positions()]
        self._pos_map = {p["title"]: p["id"] for p in self.service.list_positions()}
        v = ask_form(self, "Возврат на работу", [
            {"key": "position", "label": "Должность при возврате", "kind": "combo",
             "options": positions, "value": positions[0] if positions else ""},
            {"key": "salary", "label": "Оклад, ₽", "value": "0"},
        ])
        if not v:
            return
        try:
            self.service.reinstate(eid, self._pos_map.get(v["position"]),
                                   None, float(v["salary"] or 0))
        except ValueError as ex:
            error(self, "Ошибка", str(ex))
            return
        info(self, "Готово", "Сотрудник возвращён в активный состав.")
        self.refresh_all()

    # ---------------- экспорт ----------------
    def _export_xlsx(self, what):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile=f"{what}_{date.today().isoformat()}.xlsx")
        if not path:
            return
        sheets = {
            "movement": [("Движение кадров", ["Показатель", "Значение"],
                          list(self._movement_rows))],
            "staffing": [("Штатное расписание",
                          ["Должность", "Подразделение", "Базовый оклад",
                           "Занято", "Примечание"], list(self._staffing_rows))],
            "vacations": [("График отпусков",
                           ["Месяц", "ФИО", "Должность", "Вид", "Период",
                            "Дней", "Статус"], list(self._vp_rows))],
        }[what]
        try:
            self.service.export_xlsx(path, sheets)
        except Exception as ex:
            error(self, "Экспорт не удался", str(ex))
            return
        info(self, "Экспорт", f"Файл сохранён:\n{path}")

    def refresh_all(self):
        self.refresh_summary()
        self.refresh_staffing()
        self.refresh_vacation_plan()
        self.refresh_pension()
        self.refresh_archive()
        if not self._movement_rows:
            self.build_movement()
