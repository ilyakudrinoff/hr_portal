# -*- coding: utf-8 -*-
"""Бизнес-логика кадрового портала: приём, перевод, повышение, отпуск,
больничный, командировка, взыскания, обучение, увольнение, выход на пенсию."""

from datetime import date, datetime

from app.database import Database

EMPLOYMENT_TYPES = ["Постоянный", "Срочный договор", "Совместительство",
                    "Испытательный срок", "Стажёр", "Аутсорсинг"]

VACATION_TYPES = ["Ежегодный оплачиваемый", "Без содержания", "Учебный",
                  "По беременности и родам", "По уходу за ребёнком",
                  "Дополнительный"]

DISCIPLINARY_TYPES = ["Замечание", "Выговор", "Строгий выговор",
                      "Премия", "Благодарность", "Почётная грамота"]

TERMINATION_REASONS = [
    "Собственное желание",
    "Соглашение сторон",
    "Сокращение штата",
    "Несоответствие должности",
    " Систематические нарушения дисциплины".strip(),
    "Ликвидация организации",
    "Призыв на военную службу",
    "Обстоятельства, не зависящие от воли сторон",
    "Выход на пенсию",
]


def parse_date(s):
    if isinstance(s, (date, datetime)):
        return s if isinstance(s, date) and not isinstance(s, datetime) else s.date()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except Exception:
            continue
    raise ValueError(f"Не удалось распознать дату: {s!r}. Формат: ДД.ММ.ГГГГ")


def fmt(d):
    """date -> 'YYYY-MM-DD' для хранения в БД."""
    return d.strftime("%Y-%m-%d") if d else None


def pretty(iso):
    """'YYYY-MM-DD' -> 'ДД.ММ.ГГГГ' для отображения."""
    if not iso:
        return ""
    try:
        return parse_date(iso).strftime("%d.%m.%Y")
    except ValueError:
        return str(iso)


def full_name(row):
    ln, fn, mn = row.get("last_name", ""), row.get("first_name", ""), row.get("middle_name") or ""
    return " ".join(x for x in (ln, fn, mn) if x)


class HRService:
    def __init__(self, db=None):
        self.db = db or Database()

    # ---------- сотрудники ----------
    def list_employees(self, search="", statuses=("Работает",)):
        return self.db.list_employees(search, statuses)

    def get_employee(self, emp_id):
        return self.db.get_employee(emp_id)

    def hire(self, data):
        """Приём на работу. data — dict полей employees + опц. probation_end."""
        required = ("last_name", "first_name", "hire_date")
        missing = [k for k in required if not (data.get(k) or "").strip()]
        if missing:
            raise ValueError("Не заполнены обязательные поля: " + ", ".join(missing))
        hd = fmt(parse_date(data["hire_date"]))
        payload = {k: v for k, v in data.items()
                   if k in ("last_name", "first_name", "middle_name", "birth_date",
                            "position_id", "department_id", "salary",
                            "employment_type", "phone", "address", "email",
                            "education", "snils", "inn", "passport", "notes")}
        if payload.get("birth_date"):
            payload["birth_date"] = fmt(parse_date(payload["birth_date"]))
        payload["hire_date"] = hd
        payload["status"] = "Работает"
        eid = self.db.add_employee(payload)
        etype = payload.get("employment_type") or "Постоянный"
        self.db.add_record("events", {
            "employee_id": eid, "event_date": hd, "event_type": "Приём на работу",
            "details": f"Тип занятости: {etype}"})
        self.db.add_record("history", {
            "employee_id": eid, "hdate": hd, "field": "Приём на работу",
            "old_value": "", "new_value": etype})
        return eid

    def update_employee(self, emp_id, data):
        if data.get("birth_date"):
            data["birth_date"] = fmt(parse_date(data["birth_date"]))
        self.db.update_employee(emp_id, data)

    def transfer(self, emp_id, new_position_id, new_department_id, reason, when=None):
        """Перевод на другую должность/в другое подразделение."""
        e = self._active_or_raise(emp_id)
        d = fmt(parse_date(when)) if when else fmt(date.today())
        changes = []
        pos_changed = str(new_position_id or "") != str(e["position_id"] or "")
        dep_changed = str(new_department_id or "") != str(e["department_id"] or "")
        if not pos_changed and not dep_changed:
            raise ValueError("Выберите новую должность или подразделение — они должны отличаться от текущих.")
        upd = {}
        if pos_changed:
            upd["position_id"] = new_position_id or None
            old_t = self._position_title(e["position_id"])
            new_t = self._position_title(new_position_id)
            changes.append(f"{old_t} → {new_t}")
            self.db.add_record("history", {"employee_id": emp_id, "hdate": d,
                                           "field": "Должность", "old_value": old_t,
                                           "new_value": new_t, "note": reason})
        if dep_changed:
            upd["department_id"] = new_department_id or None
            old_d = self._dept_name(e["department_id"])
            new_d = self._dept_name(new_department_id)
            changes.append(f"{old_d} → {new_d}")
            self.db.add_record("history", {"employee_id": emp_id, "hdate": d,
                                           "field": "Подразделение", "old_value": old_d,
                                           "new_value": new_d, "note": reason})
        self.db.update_employee(emp_id, upd)
        etype = "Перевод" + (" (повышение)" if "повыш" in (reason or "").lower() else "")
        self.db.add_record("events", {"employee_id": emp_id, "event_date": d,
                                      "event_type": etype,
                                      "details": "; ".join(changes) + (f". Основание: {reason}" if reason else "")})
        return True

    def promote(self, emp_id, new_salary, reason, when=None):
        """Повышение с изменением оклада."""
        e = self._active_or_raise(emp_id)
        try:
            ns = float(new_salary)
        except (TypeError, ValueError):
            raise ValueError("Новый оклад должен быть числом.")
        if ns <= 0:
            raise ValueError("Оклад должен быть больше нуля.")
        d = fmt(parse_date(when)) if when else fmt(date.today())
        old = e["salary"] or 0
        self.db.update_employee(emp_id, {"salary": ns})
        self.db.add_record("history", {"employee_id": emp_id, "hdate": d,
                                       "field": "Оклад", "old_value": str(old),
                                       "new_value": str(ns), "note": reason})
        self.db.add_record("events", {"employee_id": emp_id, "event_date": d,
                                      "event_type": "Повышение",
                                      "details": f"Оклад {old} → {ns}. {reason or ''}".strip()})
        return True

    # ---------- отпуска / больничные / командировки ----------
    def add_vacation(self, emp_id, start, end, vtype, note=""):
        e = self._active_or_raise(emp_id)
        s, en = parse_date(start), parse_date(end)
        if en < s:
            raise ValueError("Дата окончания раньше даты начала.")
        days = (en - s).days + 1
        if vtype == "Ежегодный оплачиваемый" and days > 28:
            raise ValueError("Ежегодный оплачиваемый отпуск не может превышать 28 календарных дней.")
        self.db.add_record("vacations", {"employee_id": emp_id, "start_date": fmt(s),
                                         "end_date": fmt(en), "vtype": vtype,
                                         "status": "Запланирован", "note": note})
        self.db.add_record("events", {"employee_id": emp_id, "event_date": fmt(s),
                                      "event_type": "Отпуск",
                                      "details": f"{vtype}, {days} дн."})
        return days

    def set_vacation_status(self, rec_id, status):
        self.db.execute("UPDATE vacations SET status=? WHERE id=?", (status, rec_id))

    def add_sick(self, emp_id, start, end, diagnosis="", note=""):
        self._active_or_raise(emp_id)
        s, en = parse_date(start), parse_date(end)
        if en < s:
            raise ValueError("Дата окончания раньше даты начала.")
        days = (en - s).days + 1
        self.db.add_record("sick", {"employee_id": emp_id, "start_date": fmt(s),
                                    "end_date": fmt(en), "diagnosis": diagnosis,
                                    "note": note})
        self.db.add_record("events", {"employee_id": emp_id, "event_date": fmt(s),
                                      "event_type": "Больничный",
                                      "details": f"{days} дн. {diagnosis}".strip()})
        return days

    def add_trip(self, emp_id, start, end, destination, purpose="", note=""):
        self._active_or_raise(emp_id)
        s, en = parse_date(start), parse_date(end)
        if en < s:
            raise ValueError("Дата окончания раньше даты начала.")
        if not (destination or "").strip():
            raise ValueError("Укажите пункт назначения командировки.")
        days = (en - s).days + 1
        self.db.add_record("trips", {"employee_id": emp_id, "start_date": fmt(s),
                                     "end_date": fmt(en), "destination": destination,
                                     "purpose": purpose, "note": note})
        self.db.add_record("events", {"employee_id": emp_id, "event_date": fmt(s),
                                      "event_type": "Командировка",
                                      "details": f"{destination}, {days} дн."})
        return days

    # ---------- дисциплина / обучение ----------
    def add_disciplinary(self, emp_id, ddate, dtype, reason="", note=""):
        self._active_or_raise(emp_id)
        self.db.add_record("disciplinary", {"employee_id": emp_id,
                                            "ddate": fmt(parse_date(ddate)),
                                            "dtype": dtype, "reason": reason,
                                            "note": note})
        kind = "Взыскание" if dtype in ("Замечание", "Выговор", "Строгий выговор") else "Поощрение"
        self.db.add_record("events", {"employee_id": emp_id,
                                      "event_date": fmt(parse_date(ddate)),
                                      "event_type": kind,
                                      "details": f"{dtype}: {reason}".strip(": ")})
        return True

    def add_training(self, emp_id, tdate, program, result="", note=""):
        self._active_or_raise(emp_id)
        self.db.add_record("training", {"employee_id": emp_id,
                                        "tdate": fmt(parse_date(tdate)),
                                        "program": program, "result": result,
                                        "note": note})
        self.db.add_record("events", {"employee_id": emp_id,
                                      "event_date": fmt(parse_date(tdate)),
                                      "event_type": "Обучение",
                                      "details": f"{program}. Итог: {result or '—'}"})
        return True

    # ---------- увольнение / пенсия ----------
    def terminate(self, emp_id, term_date, reason, basis="", pension=False, note=""):
        e = self._active_or_raise(emp_id)
        d = parse_date(term_date)
        if d < parse_date(e["hire_date"]):
            raise ValueError("Дата увольнения раньше даты приёма на работу.")
        iso = fmt(d)
        self.db.add_record("terminations", {"employee_id": emp_id, "term_date": iso,
                                            "reason": reason, "basis": basis,
                                            "pension": 1 if pension else 0,
                                            "note": note})
        self.db.update_employee(emp_id, {"status": "На пенсии" if pension else "Уволен"})
        etype = "Уход на пенсию" if pension else "Увольнение"
        self.db.add_record("events", {"employee_id": emp_id, "event_date": iso,
                                      "event_type": etype,
                                      "details": f"{reason}. Основание: {basis or '—'}"})
        self.db.add_record("history", {"employee_id": emp_id, "hdate": iso,
                                       "field": "Статус", "old_value": "Работает",
                                       "new_value": e["status"] if pension else "Уволен",
                                       "note": reason})
        return True

    def reinstate(self, emp_id, position_id=None, department_id=None, salary=None):
        """Возврат сотрудника (например, ошибочное увольнение)."""
        e = self.db.get_employee(emp_id)
        if not e:
            raise ValueError("Сотрудник не найден.")
        if e["status"] == "Работает":
            raise ValueError("Сотрудник уже работает.")
        upd = {"status": "Работает"}
        if position_id:
            upd["position_id"] = position_id
        if department_id:
            upd["department_id"] = department_id
        if salary:
            upd["salary"] = float(salary)
        self.db.update_employee(emp_id, upd)
        self.db.add_record("events", {"employee_id": emp_id,
                                      "event_date": fmt(date.today()),
                                      "event_type": "Возврат на работу",
                                      "details": "Статус изменён на «Работает»"})
        return True

    # ---------- аналитика / учёт ----------
    def tenure_days(self, e):
        try:
            return (date.today() - parse_date(e["hire_date"])).days
        except Exception:
            return 0

    def age(self, e):
        try:
            b = parse_date(e["birth_date"])
        except Exception:
            return None
        today = date.today()
        years = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
        return years

    def upcoming_retirements(self, retirement_age=63, window_years=3):
        """Кандидаты на скорый выход на пенсию."""
        out = []
        for e in self.db.list_employees("", ("Работает",)):
            a = self.age(e)
            if a is None:
                continue
            if retirement_age - window_years <= a <= retirement_age + 5:
                out.append((e, a))
        out.sort(key=lambda x: -x[1])
        return out

    def stats(self):
        return {
            "by_status": self.db.count_by_status(),
            "by_department": self.db.count_by_department(),
            "by_event": self.db.count_by_event_type(),
            "avg_salary": self.db.avg_salary(),
            "payroll": self.db.total_payroll(),
        }

    # ---------- справочники ----------
    def list_departments(self):
        return self.db.list_departments()

    def list_positions(self):
        return self.db.list_positions()

    def add_department(self, name):
        if not (name or "").strip():
            raise ValueError("Название подразделения не может быть пустым.")
        return self.db.add_department(name.strip())

    def add_position(self, title, department_id=None, base_salary=0):
        if not (title or "").strip():
            raise ValueError("Название должности не может быть пустым.")
        return self.db.add_position(title.strip(), department_id, float(base_salary or 0))

    # ---------- экспорт ----------
    def export_employees_csv(self, path, rows):
        import csv
        cols = ["id", "last_name", "first_name", "middle_name", "position_title",
                "department_name", "hire_date", "salary", "status", "employment_type",
                "birth_date", "phone", "email", "snils", "inn"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(cols)
            for r in rows:
                w.writerow([r.get(c, "") for c in cols])
        return path

    def export_xlsx(self, path, sheets):
        """sheets: list[(sheet_title, header_list, rows)]"""
        from openpyxl import Workbook
        wb = Workbook()
        first = True
        for title, header, rows in sheets:
            ws = wb.active if first else wb.create_sheet()
            ws.title = title[:31]
            first = False
            ws.append(header)
            for r in rows:
                ws.append(r)
        wb.save(path)
        return path

    # ---------- вспомогательное ----------
    def _active_or_raise(self, emp_id):
        e = self.db.get_employee(emp_id)
        if not e:
            raise ValueError("Сотрудник не найден.")
        if e["status"] not in ("Работает",):
            raise ValueError(f"Операция недоступна: сотрудник со статусом «{e['status']}».")
        return e

    def _position_title(self, pid):
        if not pid:
            return "—"
        r = self.db.query_one("SELECT title FROM positions WHERE id=?", (pid,))
        return r["title"] if r else "—"

    def _dept_name(self, did):
        if not did:
            return "—"
        r = self.db.query_one("SELECT name FROM departments WHERE id=?", (did,))
        return r["name"] if r else "—"
