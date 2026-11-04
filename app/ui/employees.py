# -*- coding: utf-8 -*-
"""Вкладка «Сотрудники»: список, карточка, приём/редактирование,
переводы, повышения, отпуска, больничные, командировки, дисциплина,
обучение, увольнение и выход на пенсию."""

import tkinter as tk
from datetime import date
from tkinter import ttk, filedialog

from app.services import (EMPLOYMENT_TYPES, VACATION_TYPES, DISCIPLINARY_TYPES,
                          TERMINATION_REASONS, HRService, full_name, pretty)
from app.ui.common import (ask_form, confirm, error, info, STATUS_COLORS,
                           CARD, OK, DANGER, MUTED)


class EmployeesFrame(ttk.Frame):
    def __init__(self, master, service: HRService):
        super().__init__(master)
        self.service = service
        self.all_rows = []
        self._build_list_view()
        self._build_card_view()

    # ================= СПИСОК =================
    def _build_list_view(self):
        f = self.list_frame = ttk.Frame(self, style="Card.TFrame", padding=12)
        f.pack(fill="both", expand=True)

        top = ttk.Frame(f, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Сотрудники организации",
                  style="H1.TLabel").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filter())
        ent = ttk.Entry(top, textvariable=self.search_var, width=34)
        ent.pack(side="right")
        ttk.Label(ent.master, text="Поиск: ", style="Card.TLabel").pack(
            side="right", anchor="e")

        filters = ttk.Frame(f, style="Card.TFrame")
        filters.pack(fill="x", pady=(8, 4))
        self.status_var = tk.StringVar(value="Работает")
        for txt, val in [("Работает", "Работает"),
                         ("Уволенные", "Уволен"),
                         ("На пенсии", "На пенсии"),
                         ("Все", "")]:
            ttk.Radiobutton(filters, text=txt, value=val,
                            variable=self.status_var,
                            command=self.apply_filter).pack(side="left", padx=(0, 10))
        ttk.Button(filters, text="+ Принять на работу",
                   style="Accent.TButton",
                   command=self.hire).pack(side="right")
        ttk.Button(filters, text="Экспорт CSV",
                   command=self.export_csv).pack(side="right", padx=(0, 8))

        cols = ("id", "fio", "position", "dept", "hire", "salary", "status")
        heads = ("№", "ФИО", "Должность", "Подразделение",
                 "Приём", "Оклад", "Статус")
        widths = (45, 230, 190, 160, 95, 95, 95)
        self.tree = ttk.Treeview(f, columns=cols, show="headings",
                                 selectmode="browse")
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w", stretch=(c in ("fio", "position")))
        self.tree.pack(fill="both", expand=True, pady=(4, 0))
        self.tree.tag_configure("works", foreground=OK)
        self.tree.tag_configure("fired", foreground=DANGER)
        self.tree.tag_configure("pension", foreground="#8a5fb0")
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.tree.bind("<Return>", lambda e: self.open_selected())

        self.count_lbl = ttk.Label(f, text="", style="Muted.TLabel")
        self.count_lbl.pack(anchor="w", pady=(6, 0))

    def refresh(self):
        self.all_rows = self.service.list_employees("", None)
        self.apply_filter()

    def apply_filter(self):
        st = self.status_var.get()
        q = self.search_var.get().lower().strip()
        statuses = ("Работает", "Уволен", "На пенсии") if st == "" else (st,)
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for r in self.all_rows:
            if statuses and r["status"] not in statuses:
                continue
            hay = " ".join(str(r.get(k, "")) for k in
                           ("last_name", "first_name", "middle_name",
                            "position_title", "department_name")).lower()
            if q and q not in hay:
                continue
            tag = {"Работает": "works", "Уволен": "fired"}.get(
                r["status"], "pension")
            self.tree.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], full_name(r), r.get("position_title") or "—",
                r.get("department_name") or "—", pretty(r["hire_date"]),
                f"{r['salary'] or 0:,.0f}".replace(",", " "), r["status"]))
            shown += 1
        self.count_lbl.config(text=f"Показано: {shown} из {len(self.all_rows)}")

    def selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def open_selected(self):
        eid = self.selected_id()
        if eid:
            self.show_card(eid)

    # ================= КАРТОЧКА =================
    def _build_card_view(self):
        self.card_frame = ttk.Frame(self, style="Card.TFrame", padding=12)
        head = ttk.Frame(self.card_frame, style="Card.TFrame")
        head.pack(fill="x")
        ttk.Button(head, text="← К списку", command=self.show_list).pack(side="left")
        self.card_title = ttk.Label(head, text="", style="H1.TLabel")
        self.card_title.pack(side="left", padx=14)
        self.card_status = ttk.Label(head, text="", style="Card.TLabel")
        self.card_status.pack(side="right")

        body = ttk.Frame(self.card_frame, style="Card.TFrame")
        body.pack(fill="both", expand=True, pady=10)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)

        # левая колонка — личные данные + действия
        left = ttk.Frame(body, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.info_lbl = ttk.Label(left, text="", style="Card.TLabel",
                                  justify="left", font=("Consolas", 10))
        self.info_lbl.pack(anchor="nw")

        acts = ttk.LabelFrame(left, text="Кадровые операции", style="Card.TFrame")
        acts.pack(fill="x", pady=(12, 0))
        grid = {"sticky": "ew", "padx": 6, "pady": 2}
        ttk.Button(acts, text="Редактировать данные",
                   command=self.edit).grid(row=0, column=0, **grid)
        ttk.Button(acts, text="Перевод / повышение",
                   command=self.transfer_promote).grid(row=0, column=1, **grid)
        ttk.Button(acts, text="Отправить в отпуск",
                   command=lambda: self.add_vacation()).grid(row=1, column=0, **grid)
        ttk.Button(acts, text="Больничный лист",
                   command=self.add_sick).grid(row=1, column=1, **grid)
        ttk.Button(acts, text="Командировка",
                   command=self.add_trip).grid(row=2, column=0, **grid)
        ttk.Button(acts, text="Взыскание / поощрение",
                   command=self.add_disciplinary).grid(row=2, column=1, **grid)
        ttk.Button(acts, text="Обучение / квалификация",
                   command=self.add_training).grid(row=3, column=0, **grid)
        ttk.Button(acts, text="Увольнение / пенсия", style="Danger.TButton",
                   command=self.terminate).grid(row=3, column=1, **grid)
        acts.columnconfigure(0, weight=1)
        acts.columnconfigure(1, weight=1)

        # правая колонка — вкладки записей
        self.nb = ttk.Notebook(body)
        self.nb.grid(row=0, column=1, sticky="nsew")
        self.record_trees = {}
        tabs = [
            ("events", "События", ("event_date", "event_type", "details"),
             ("Дата", "Событие", "Подробности")),
            ("vacations", "Отпуска", ("start_date", "end_date", "vtype", "status"),
             ("Начало", "Окончание", "Вид", "Статус")),
            ("sick", "Больничные", ("start_date", "end_date", "diagnosis"),
             ("Начало", "Окончание", "Диагноз")),
            ("trips", "Командировки", ("start_date", "end_date", "destination", "purpose"),
             ("Начало", "Окончание", "Куда", "Цель")),
            ("disciplinary", "Дисциплина", ("ddate", "dtype", "reason"),
             ("Дата", "Тип", "Причина")),
            ("training", "Обучение", ("tdate", "program", "result"),
             ("Дата", "Программа", "Результат")),
            ("history", "История изменений", ("hdate", "field", "old_value", "new_value"),
             ("Дата", "Что", "Было", "Стало")),
            ("terminations", "Увольнения", ("term_date", "reason", "basis", "pension"),
             ("Дата", "Причина", "Основание", "Пенсия")),
        ]
        for key, title, cols, heads in tabs:
            fr = ttk.Frame(self.nb)
            self.nb.add(fr, text=title)
            t = ttk.Treeview(fr, columns=cols, show="headings")
            for c, h in zip(cols, heads):
                t.heading(c, text=h)
                t.column(c, width=110, stretch=(c == cols[-1] or h in
                                                 ("Подробности", "Причина", "Программа")))
            vsb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
            t.configure(yscrollcommand=vsb.set)
            t.pack(side="left", fill="both", expand=True)
            vsb.pack(side="right", fill="y")
            self.record_trees[key] = t
        if self.record_trees:
            self.record_trees["vacations"].tag_configure("past", foreground=MUTED)

    # ---------- навигация ----------
    def show_list(self):
        self.current_emp = None
        self.card_frame.pack_forget()
        self.list_frame.pack(fill="both", expand=True)
        self.refresh()

    def show_card(self, emp_id):
        self.current_emp = emp_id
        self.list_frame.pack_forget()
        self.card_frame.pack(fill="both", expand=True)
        self.reload_card()

    def reload_card(self):
        e = self.service.get_employee(self.current_emp)
        if not e:
            self.show_list()
            return
        name = full_name(e)
        self.card_title.config(text=name)
        color = {"Работает": OK, "Уволен": DANGER}.get(e["status"], "#8a5fb0")
        self.card_status.config(text=e["status"], foreground=color)
        age = self.service.age(e)
        tenure = self.service.tenure_days(e)
        yrs = tenure // 365
        lines = [
            ("Должность:", e.get("position_title") or "—"),
            ("Подразделение:", e.get("department_name") or "—"),
            ("Оклад:", f"{e['salary'] or 0:,.0f} ₽".replace(",", " ")),
            ("Тип занятости:", e.get("employment_type") or "—"),
            ("Приём на работу:", pretty(e["hire_date"])),
            ("Дата рождения:", f"{pretty(e['birth_date'])}"
             + (f"  ({age} лет)" if age is not None else "")),
            ("Стаж в компании:", f"{yrs} г. {int((tenure % 365)/30)} мес."),
            ("Телефон:", e.get("phone") or "—"),
            ("E-mail:", e.get("email") or "—"),
            ("Адрес:", e.get("address") or "—"),
            ("Образование:", e.get("education") or "—"),
            ("СНИЛС:", e.get("snils") or "—"),
            ("ИНН:", e.get("inn") or "—"),
            ("Паспорт:", e.get("passport") or "—"),
        ]
        if e.get("notes"):
            lines.append(("Примечание:", e["notes"]))
        self.info_lbl.config(
            text="\n".join(f"{k:<20}{v}" for k, v in lines))
        for key, t in self.record_trees.items():
            t.delete(*t.get_children())
            for rec in self.service.db.list_records(key, self.current_emp):
                vals = tuple(pretty(rec[c]) if c.endswith("_date") or
                             c in ("event_date", "ddate", "tdate", "hdate")
                             else ("Да" if c == "pension" and rec[c] else
                                   rec.get(c, ""))
                             for c in t["columns"])
                tags = ()
                if key == "vacations" and rec["end_date"] < date.today().isoformat():
                    tags = ("past",)
                t.insert("", "end", values=vals, tags=tags)

    # ---------- операции ----------
    def _person_fields(self, e=None):
        positions = [""] + [p["title"] for p in self.service.list_positions()]
        pos_map = {p["title"]: p["id"] for p in self.service.list_positions()}
        deps = [""] + [d["name"] for d in self.service.list_departments()]
        dep_map = {d["name"]: d["id"] for d in self.service.list_departments()}
        self._pos_map, self._dep_map = pos_map, dep_map
        g = lambda k: (e or {}).get(k) or ""
        return [
            {"key": "last_name", "label": "Фамилия *", "value": g("last_name")},
            {"key": "first_name", "label": "Имя *", "value": g("first_name")},
            {"key": "middle_name", "label": "Отчество", "value": g("middle_name")},
            {"key": "birth_date", "label": "Дата рождения (ДД.ММ.ГГГГ)",
             "value": pretty(g("birth_date"))},
            {"key": "hire_date", "label": "Дата приёма * (ДД.ММ.ГГГГ)",
             "value": pretty(g("hire_date")) or date.today().strftime("%d.%m.%Y")},
            {"key": "position", "label": "Должность", "kind": "combo",
             "options": positions, "value": (e or {}).get("position_title") or ""},
            {"key": "department", "label": "Подразделение", "kind": "combo",
             "options": deps, "value": (e or {}).get("department_name") or ""},
            {"key": "salary", "label": "Оклад, ₽",
             "value": str(int(g("salary") or 0))},
            {"key": "employment_type", "label": "Тип занятости", "kind": "combo",
             "options": EMPLOYMENT_TYPES, "value": g("employment_type") or "Постоянный"},
            {"key": "phone", "label": "Телефон", "value": g("phone")},
            {"key": "email", "label": "E-mail", "value": g("email")},
            {"key": "address", "label": "Адрес проживания", "value": g("address")},
            {"key": "education", "label": "Образование", "value": g("education")},
            {"key": "snils", "label": "СНИЛС", "value": g("snils")},
            {"key": "inn", "label": "ИНН", "value": g("inn")},
            {"key": "passport", "label": "Паспорт", "value": g("passport")},
            {"key": "notes", "label": "Примечание", "value": g("notes")},
        ]

    def hire(self):
        v = ask_form(self, "Приём на работу", self._person_fields())
        if not v:
            return
        try:
            data = self._to_payload(v)
            eid = self.service.hire(data)
        except ValueError as ex:
            error(self, "Ошибка приёма", str(ex))
            return
        info(self, "Приём оформлен",
             f"Сотрудник принят, кадровая запись создана (ID {eid}).")
        self.refresh()
        self.show_card(eid)

    def edit(self):
        e = self.service.get_employee(self.current_emp)
        v = ask_form(self, "Редактирование карточки сотрудника",
                     self._person_fields(e))
        if not v:
            return
        try:
            payload = self._to_payload(v, editing=True)
            self.service.update_employee(self.current_emp, payload)
        except ValueError as ex:
            error(self, "Ошибка", str(ex))
            return
        self.reload_card()

    def _to_payload(self, v, editing=False):
        out = {
            "last_name": v["last_name"], "first_name": v["first_name"],
            "middle_name": v["middle_name"],
            "position_id": self._pos_map.get(v["position"]),
            "department_id": self._dep_map.get(v["department"]),
            "employment_type": v["employment_type"],
            "phone": v["phone"], "email": v["email"], "address": v["address"],
            "education": v["education"], "snils": v["snils"],
            "inn": v["inn"], "passport": v["passport"], "notes": v["notes"],
        }
        try:
            out["salary"] = float(v["salary"].replace(" ", "").replace("₽", "") or 0)
        except ValueError:
            raise ValueError("Оклад должен быть числом.")
        if v["birth_date"]:
            out["birth_date"] = v["birth_date"]
        if not editing:
            out["hire_date"] = v["hire_date"]
        return out

    def transfer_promote(self):
        e = self.service.get_employee(self.current_emp)
        positions = [p["title"] for p in self.service.list_positions()]
        deps = [d["name"] for d in self.service.list_departments()]
        self._pos_map = {p["title"]: p["id"] for p in self.service.list_positions()}
        self._dep_map = {d["name"]: d["id"] for d in self.service.list_departments()}
        fields = [
            {"key": "what", "label": "Операция", "kind": "combo",
             "options": ["Перевод на другую должность", "Перевод в подразделение",
                         "Перевод + новое назначение", "Повышение оклада"],
             "value": "Перевод на другую должность"},
            {"key": "when", "label": "Дата (ДД.ММ.ГГГГ)",
             "value": date.today().strftime("%d.%m.%Y")},
            {"key": "position", "label": "Новая должность", "kind": "combo",
             "options": positions, "value": e.get("position_title") or ""},
            {"key": "department", "label": "Новое подразделение", "kind": "combo",
             "options": deps, "value": e.get("department_name") or ""},
            {"key": "salary", "label": "Новый оклад, ₽",
             "value": str(int(e["salary"] or 0))},
            {"key": "reason", "label": "Основание / причина", "value": ""},
        ]
        v = ask_form(self, "Перевод / повышение", fields)
        if not v:
            return
        try:
            what = v["what"]
            if what.startswith("Повышение"):
                self.service.promote(self.current_emp, v["salary"],
                                     v["reason"] or "Повышение оклада", v["when"])
            else:
                pid = did = None
                if "должн" in what or what == "Перевод + новое назначение":
                    pid = self._pos_map.get(v["position"])
                if "подразд" in what or what == "Перевод + новое назначение":
                    did = self._dep_map.get(v["department"])
                self.service.transfer(self.current_emp, pid, did,
                                      v["reason"], v["when"])
                if what == "Перевод + новое назначение" and v["salary"]:
                    new_sal = float(v["salary"].replace(" ", "") or 0)
                    if new_sal and new_sal != (e["salary"] or 0):
                        self.service.promote(self.current_emp, new_sal,
                                             "Изменение оклада при переводе",
                                             v["when"])
        except ValueError as ex:
            error(self, "Ошибка перевода", str(ex))
            return
        self.reload_card()

    def add_vacation(self):
        fields = [
            {"key": "start", "label": "С какого числа",
             "value": date.today().strftime("%d.%m.%Y")},
            {"key": "end", "label": "По какое число",
             "value": ""},
            {"key": "days", "label": "или количество дней (28)", "kind": "spin",
             "min": 1, "max": 365, "value": 28},
            {"key": "vtype", "label": "Вид отпуска", "kind": "combo",
             "options": VACATION_TYPES, "value": VACATION_TYPES[0]},
            {"key": "note", "label": "Примечание", "value": ""},
        ]
        v = ask_form(self, "Оформление отпуска", fields)
        if not v:
            return
        try:
            start = v["start"]
            end = v["end"]
            if not end:
                from datetime import timedelta
                from app.services import parse_date, fmt
                end = fmt(parse_date(start) + timedelta(days=int(v["days"]) - 1))
            days = self.service.add_vacation(self.current_emp, start, end,
                                             v["vtype"], v["note"])
        except ValueError as ex:
            error(self, "Ошибка отпуска", str(ex))
            return
        info(self, "Отпуск оформлен", f"Дней: {days}. Запись добавлена в график.")
        self.reload_card()

    def add_sick(self):
        fields = [
            {"key": "start", "label": "С какого числа",
             "value": date.today().strftime("%d.%m.%Y")},
            {"key": "end", "label": "По какое число", "value": ""},
            {"key": "diag", "label": "Диагноз / код БЛ", "value": ""},
            {"key": "note", "label": "Примечание", "value": ""},
        ]
        v = ask_form(self, "Больничный лист", fields)
        if not v:
            return
        try:
            self.service.add_sick(self.current_emp, v["start"], v["end"],
                                  v["diag"], v["note"])
        except ValueError as ex:
            error(self, "Ошибка", str(ex))
            return
        self.reload_card()

    def add_trip(self):
        fields = [
            {"key": "start", "label": "С какого числа",
             "value": date.today().strftime("%d.%m.%Y")},
            {"key": "end", "label": "По какое число", "value": ""},
            {"key": "dest", "label": "Пункт назначения", "value": ""},
            {"key": "purpose", "label": "Цель командировки", "value": ""},
            {"key": "note", "label": "Примечание", "value": ""},
        ]
        v = ask_form(self, "Командировка", fields)
        if not v:
            return
        try:
            self.service.add_trip(self.current_emp, v["start"], v["end"],
                                  v["dest"], v["purpose"], v["note"])
        except ValueError as ex:
            error(self, "Ошибка", str(ex))
            return
        self.reload_card()

    def add_disciplinary(self):
        fields = [
            {"key": "ddate", "label": "Дата",
             "value": date.today().strftime("%d.%m.%Y")},
            {"key": "dtype", "label": "Тип", "kind": "combo",
             "options": DISCIPLINARY_TYPES, "value": DISCIPLINARY_TYPES[0]},
            {"key": "reason", "label": "Причина", "value": ""},
            {"key": "note", "label": "Номер приказа", "value": ""},
        ]
        v = ask_form(self, "Взыскание / поощрение", fields)
        if not v:
            return
        try:
            self.service.add_disciplinary(self.current_emp, v["ddate"],
                                          v["dtype"], v["reason"], v["note"])
        except ValueError as ex:
            error(self, "Ошибка", str(ex))
            return
        self.reload_card()

    def add_training(self):
        fields = [
            {"key": "tdate", "label": "Дата",
             "value": date.today().strftime("%d.%m.%Y")},
            {"key": "program", "label": "Программа обучения", "value": ""},
            {"key": "result", "label": "Результат / документ", "value": ""},
            {"key": "note", "label": "Примечание", "value": ""},
        ]
        v = ask_form(self, "Обучение / повышение квалификации", fields)
        if not v:
            return
        try:
            self.service.add_training(self.current_emp, v["tdate"],
                                      v["program"], v["result"], v["note"])
        except ValueError as ex:
            error(self, "Ошибка", str(ex))
            return
        self.reload_card()

    def terminate(self):
        e = self.service.get_employee(self.current_emp)
        age = self.service.age(e)
        near_pension = age is not None and age >= 58
        fields = [
            {"key": "when", "label": "Дата увольнения",
             "value": date.today().strftime("%d.%m.%Y")},
            {"key": "reason", "label": "Причина", "kind": "combo",
             "options": TERMINATION_REASONS,
             "value": "Выход на пенсию" if near_pension else TERMINATION_REASONS[0]},
            {"key": "basis", "label": "Основание (ст. ТК РФ / приказ)",
             "value": "ТК РФ ст. 77 п. 3" if near_pension else "ТК РФ ст. 80"},
            {"key": "pension", "label": "Это уход на пенсию?", "kind": "combo",
             "options": ["Нет", "Да"], "value": "Да" if near_pension else "Нет"},
            {"key": "note", "label": "Примечание", "value": ""},
        ]
        v = ask_form(self, "Увольнение / выход на пенсию", fields)
        if not v:
            return
        pension = v["pension"] == "Да"
        if not confirm(self, "Подтверждение",
                       f"{full_name(e)}: {'уход на пенсию' if pension else 'увольнение'} "
                       f"с {pretty(v['when'])}?\n{v['reason']}"):
            return
        try:
            self.service.terminate(self.current_emp, v["when"], v["reason"],
                                   v["basis"], pension, v["note"])
        except ValueError as ex:
            error(self, "Ошибка увольнения", str(ex))
            return
        info(self, "Оформлено",
             "Сотрудник снят с активного кадрового учёта; запись сохранена в архиве.")
        self.reload_card()

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="employees.csv")
        if not path:
            return
        rows = [dict(r) for r in self.all_rows]
        self.service.export_employees_csv(path, rows)
        info(self, "Экспорт", f"Файл сохранён:\n{path}")
