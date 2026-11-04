# -*- coding: utf-8 -*-
"""Заполнение базы демо-данными при первом запуске."""

from datetime import date, timedelta

DEPARTMENTS = ["Генеральная дирекция", "Бухгалтерия", "Отдел кадров",
               "ИТ-отдел", "Отдел продаж", "Юридический отдел",
               "Производственный цех", "Склад"]

POSITIONS = [
    ("Генеральный директор", "Генеральная дирекция", 250000),
    ("Главный бухгалтер", "Бухгалтерия", 120000),
    ("Бухгалтер", "Бухгалтерия", 70000),
    ("Начальник отдела кадров", "Отдел кадров", 100000),
    ("Инспектор по кадрам", "Отдел кадров", 60000),
    ("Системный администратор", "ИТ-отдел", 80000),
    ("Программист", "ИТ-отдел", 130000),
    ("Менеджер по продажам", "Отдел продаж", 75000),
    ("Юрист", "Юридический отдел", 95000),
    ("Начальник цеха", "Производственный цех", 110000),
    ("Оператор станка", "Производственный цех", 55000),
    ("Заведующий складом", "Склад", 70000),
    ("Кладовщик", "Склад", 45000),
]

EMPLOYEES = [
    # (фамилия, имя, отчество, д.рожд., д.приёма, должность, оклад, тип, тел, email)
    ("Иванов", "Сергей", "Петрович", "1965-03-12", "2010-01-11",
     "Генеральный директор", 250000, "Постоянный", "+7-900-111-2233", "s.ivanov@company.ru"),
    ("Петрова", "Анна", "Викторовна", "1978-07-25", "2012-04-02",
     "Главный бухгалтер", 120000, "Постоянный", "+7-900-222-3344", "a.petrova@company.ru"),
    ("Сидорова", "Мария", "Игоревна", "1990-11-03", "2018-09-10",
     "Бухгалтер", 70000, "Постоянный", "+7-900-333-4455", "m.sidorova@company.ru"),
    ("Кузнецова", "Ольга", "Дмитриевна", "1982-02-17", "2015-06-01",
     "Начальник отдела кадров", 100000, "Постоянный", "+7-900-444-5566", "o.kuznetsova@company.ru"),
    ("Смирнова", "Екатерина", "Андреевна", "1995-05-30", "2021-02-15",
     "Инспектор по кадрам", 60000, "Постоянный", "+7-900-555-6677", "e.smirnova@company.ru"),
    ("Козлов", "Дмитрий", "Алексеевич", "1988-09-14", "2019-05-13",
     "Системный администратор", 80000, "Постоянный", "+7-900-666-7788", "d.kozlov@company.ru"),
    ("Новиков", "Артём", "Сергеевич", "1993-12-01", "2020-10-05",
     "Программист", 130000, "Постоянный", "+7-900-777-8899", "a.novikov@company.ru"),
    ("Морозова", "Виктория", "Павловна", "1991-04-22", "2017-03-20",
     "Менеджер по продажам", 75000, "Постоянный", "+7-900-888-9900", "v.morozova@company.ru"),
    ("Волков", "Николай", "Иванович", "1985-08-09", "2014-01-08",
     "Юрист", 95000, "Постоянный", "+7-900-999-0011", "n.volkov@company.ru"),
    ("Соколов", "Владимир", "Николаевич", "1970-01-15", "2005-05-04",
     "Начальник цеха", 110000, "Постоянный", "+7-900-101-2030", "v.sokolov@company.ru"),
    ("Лебедев", "Павел", "Олегович", "1997-06-18", "2022-08-01",
     "Оператор станка", 55000, "Испытательный срок", "+7-900-202-3040", ""),
    ("Егорова", "Наталья", "Сергеевна", "1983-10-28", "2016-11-14",
     "Заведующий складом", 70000, "Постоянный", "+7-900-303-4050", ""),
    ("Титов", "Андрей", "Владимирович", "1994-02-05", "2023-01-09",
     "Кладовщик", 45000, "Срочный договор", "+7-900-404-5060", ""),
]


def seed_if_empty(db):
    if db.query_one("SELECT COUNT(*) c FROM employees")["c"] > 0:
        return False
    dep_ids = {}
    for name in DEPARTMENTS:
        dep_ids[name] = db.add_department(name)
    pos_ids = {}
    for title, dep, sal in POSITIONS:
        pos_ids[title] = db.add_position(title, dep_ids[dep], sal)

    today = date.today()
    pos_dept = {t: d for t, d, _ in POSITIONS}
    for ln, fn, mn, bd, hd, pos, sal, etype, phone, email in EMPLOYEES:
        eid = db.add_employee({
            "last_name": ln, "first_name": fn, "middle_name": mn,
            "birth_date": bd, "hire_date": hd,
            "position_id": pos_ids[pos],
            "department_id": dep_ids[pos_dept[pos]],
            "salary": sal, "employment_type": etype,
            "phone": phone, "email": email, "status": "Работает",
        })
        db.add_record("events", {"employee_id": eid, "event_date": hd,
                                 "event_type": "Приём на работу",
                                 "details": f"Тип занятости: {etype}"})

    # Демо-события в жизни сотрудников
    emp = lambda n: db.query_one(
        "SELECT id FROM employees WHERE last_name=?", (n,))["id"]

    db.add_record("vacations", {"employee_id": emp("Смирнова"),
                                "start_date": (today + timedelta(days=14)).isoformat(),
                                "end_date": (today + timedelta(days=27)).isoformat(),
                                "vtype": "Ежегодный оплачиваемый",
                                "status": "Запланирован", "note": ""})
    db.add_record("sick", {"employee_id": emp("Козлов"),
                           "start_date": (today - timedelta(days=5)).isoformat(),
                           "end_date": (today - timedelta(days=1)).isoformat(),
                           "diagnosis": "ОРВИ", "note": ""})
    db.add_record("trips", {"employee_id": emp("Морозова"),
                            "start_date": (today + timedelta(days=7)).isoformat(),
                            "end_date": (today + timedelta(days=11)).isoformat(),
                            "destination": "г. Казань",
                            "purpose": "Переговоры с клиентом", "note": ""})
    db.add_record("disciplinary", {"employee_id": emp("Титов"),
                                   "ddate": (today - timedelta(days=30)).isoformat(),
                                   "dtype": "Благодарность",
                                   "reason": "Образцовое выполнение обязанностей",
                                   "note": ""})
    db.add_record("training", {"employee_id": emp("Новиков"),
                               "tdate": (today - timedelta(days=60)).isoformat(),
                               "program": "Курс «Безопасность Linux»",
                               "result": "Удостоверение №Л-451", "note": ""})
    db.add_record("history", {"employee_id": emp("Петрова"),
                              "hdate": "2018-03-01", "field": "Оклад",
                              "old_value": "95000", "new_value": "120000",
                              "note": "Индексация"})
    db.add_record("events", {"employee_id": emp("Петрова"),
                             "event_date": "2018-03-01", "event_type": "Повышение",
                             "details": "Оклад 95000 → 120000. Индексация"})

    # Уволенные и пенсионеры для полноты учёта
    old_id = db.add_employee({"last_name": "Фёдоров", "first_name": "Игорь",
                              "middle_name": "Михайлович", "birth_date": "1958-06-20",
                              "hire_date": "1995-02-01",
                              "position_id": pos_ids["Оператор станка"],
                              "department_id": dep_ids["Производственный цех"],
                              "salary": 50000, "status": "На пенсии",
                              "employment_type": "Постоянный"})
    term_d = (today - timedelta(days=200)).isoformat()
    db.add_record("terminations", {"employee_id": old_id, "term_date": term_d,
                                   "reason": "Выход на пенсию",
                                   "basis": "ТК РФ ст. 77 п. 3", "pension": 1,
                                   "note": "Стаж более 25 лет"})
    db.add_record("events", {"employee_id": old_id, "event_date": term_d,
                             "event_type": "Уход на пенсию",
                             "details": "Выход на пенсию. Основание: ТК РФ ст. 77 п. 3"})

    fired_id = db.add_employee({"last_name": "Зайцев", "first_name": "Роман",
                                "middle_name": "", "birth_date": "1992-03-08",
                                "hire_date": "2022-05-16",
                                "position_id": pos_ids["Менеджер по продажам"],
                                "department_id": dep_ids["Отдел продаж"],
                                "salary": 75000, "status": "Уволен",
                                "employment_type": "Постоянный"})
    fz_d = (today - timedelta(days=90)).isoformat()
    db.add_record("terminations", {"employee_id": fired_id, "term_date": fz_d,
                                   "reason": "Собственное желание",
                                   "basis": "ТК РФ ст. 80", "pension": 0,
                                   "note": ""})
    db.add_record("events", {"employee_id": fired_id, "event_date": fz_d,
                             "event_type": "Увольнение",
                             "details": "Собственное желание. Основание: ТК РФ ст. 80"})
    return True
