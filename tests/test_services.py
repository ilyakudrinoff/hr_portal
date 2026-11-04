# -*- coding: utf-8 -*-
"""Тесты бизнес-логики кадрового портала (без GUI)."""

import os
import tempfile

import pytest

from app.database import Database
from app.services import HRService, parse_date, pretty


@pytest.fixture()
def svc(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    return HRService(db)


def make_employee(svc, last="Тестов", first="Иван", position=None, dept=None,
                  birth="1960-01-10", hire="2020-01-01", salary=50000):
    return svc.hire({
        "last_name": last, "first_name": first, "middle_name": "Петрович",
        "birth_date": birth, "hire_date": hire,
        "position_id": position, "department_id": dept,
        "salary": salary, "employment_type": "Постоянный",
    })


def test_hire_creates_records(svc):
    eid = make_employee(svc)
    e = svc.get_employee(eid)
    assert e["status"] == "Работает"
    assert e["hire_date"] == "2020-01-01"
    events = svc.db.list_records("events", eid)
    assert any(ev["event_type"] == "Приём на работу" for ev in events)


def test_hire_requires_fields(svc):
    with pytest.raises(ValueError):
        svc.hire({"last_name": "", "first_name": "", "hire_date": ""})


def test_transfer_and_history(svc):
    pid1 = svc.add_position("Программист")
    pid2 = svc.add_position("Ведущий программист")
    did = svc.add_department("ИТ")
    eid = make_employee(svc, position=pid1, dept=did)
    svc.transfer(eid, pid2, did, "Повышение по результатам аттестации")
    e = svc.get_employee(eid)
    assert e["position_id"] == pid2
    hist = svc.db.list_records("history", eid)
    assert any(h["field"] == "Должность" for h in hist)


def test_transfer_no_change_raises(svc):
    pid1 = svc.add_position("Кладовщик")
    eid = make_employee(svc, position=pid1)
    with pytest.raises(ValueError):
        svc.transfer(eid, pid1, None, "")


def test_promote(svc):
    eid = make_employee(svc, salary=50000)
    svc.promote(eid, 70000, "Пересмотр оклада")
    assert svc.get_employee(eid)["salary"] == 70000
    assert any(ev["event_type"] == "Повышение"
               for ev in svc.db.list_records("events", eid))


def test_vacation_rules(svc):
    eid = make_employee(svc)
    days = svc.add_vacation(eid, "2026-07-01", "2026-07-28",
                            "Ежегодный оплачиваемый")
    assert days == 28
    with pytest.raises(ValueError):
        svc.add_vacation(eid, "2026-08-01", "2026-09-15",
                         "Ежегодный оплачиваемый")
    with pytest.raises(ValueError):
        svc.add_vacation(eid, "2026-08-10", "2026-08-01", "Учебный")


def test_sick_and_trip(svc):
    eid = make_employee(svc)
    assert svc.add_sick(eid, "2026-05-04", "2026-05-10", "ОРВИ") == 7
    assert svc.add_trip(eid, "2026-06-01", "2026-06-05", "г. Псков",
                        "Выставка") == 5
    with pytest.raises(ValueError):
        svc.add_trip(eid, "2026-06-01", "2026-06-05", "")


def test_terminate_and_pension(svc):
    eid = make_employee(svc, hire="2020-01-01")
    with pytest.raises(ValueError):
        svc.terminate(eid, "2019-01-01", "Собственное желание")
    svc.terminate(eid, "2026-10-01", "Выход на пенсию",
                  "ТК РФ ст. 77 п. 3", pension=True)
    e = svc.get_employee(eid)
    assert e["status"] == "На пенсии"
    # операции недоступны уволенному
    with pytest.raises(ValueError):
        svc.add_vacation(eid, "2026-11-01", "2026-11-10", "Без содержания")
    # возврат на работу
    svc.reinstate(eid, None, None, 40000)
    assert svc.get_employee(eid)["status"] == "Работает"


def test_retirement_forecast(svc):
    from datetime import date, timedelta
    today = date.today()
    age62 = (today - timedelta(days=int(62.5 * 365.25))).isoformat()
    eid = make_employee(svc, birth=age62)
    lst = svc.upcoming_retirements()
    assert any(x[0]["id"] == eid for x in lst)


def test_stats(svc):
    make_employee(svc, salary=60000)
    make_employee(svc, last="Второй", salary=80000)
    st = svc.stats()
    assert st["avg_salary"] == 70000
    assert st["payroll"] == 140000


def test_dates_formats():
    assert parse_date("05.11.2026") == parse_date("2026-11-05")
    assert pretty("2026-11-05") == "05.11.2026"
    with pytest.raises(ValueError):
        parse_date("не дата")


def test_export_csv(svc, tmp_path):
    eid = make_employee(svc)
    rows = svc.list_employees("", ("Работает",))
    p = svc.export_employees_csv(str(tmp_path / "e.csv"), rows)
    assert os.path.exists(p) and os.path.getsize(p) > 0


def test_seed_demo(svc):
    from app.seed import seed_if_empty
    assert seed_if_empty(svc.db) is True
    assert seed_if_empty(svc.db) is False  # идемпотентность
    assert len(svc.list_employees("", ("Работает",))) >= 10
