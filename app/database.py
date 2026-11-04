# -*- coding: utf-8 -*-
"""Слой работы с базой данных (SQLite) для портала по работе с кадрами."""

import os
import sqlite3

APP_DIR_NAME = "HRPortal"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    head_employee_id INTEGER REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    department_id INTEGER REFERENCES departments(id),
    base_salary REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    birth_date TEXT,
    hire_date TEXT NOT NULL,
    position_id INTEGER REFERENCES positions(id),
    department_id INTEGER REFERENCES departments(id),
    salary REAL DEFAULT 0,
    employment_type TEXT DEFAULT 'Постоянный',
    status TEXT NOT NULL DEFAULT 'Работает',
    phone TEXT, address TEXT, email TEXT,
    education TEXT,
    snils TEXT, inn TEXT, passport TEXT,
    notes TEXT
);

-- Кадровые события: приём, перевод, повышение, изменение оклада
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    event_date TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT
);

-- Отпуска (основной, без содержания, учебный, декрет...)
CREATE TABLE IF NOT EXISTS vacations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    vtype TEXT NOT NULL DEFAULT 'Ежегодный оплачиваемый',
    status TEXT NOT NULL DEFAULT 'Запланирован',
    note TEXT
);

-- Больничные листы
CREATE TABLE IF NOT EXISTS sick_leaves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    diagnosis TEXT,
    note TEXT
);

-- Командировки
CREATE TABLE IF NOT EXISTS business_trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    destination TEXT,
    purpose TEXT,
    note TEXT
);

-- Дисциплинарные взыскания и поощрения
CREATE TABLE IF NOT EXISTS disciplinary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    ddate TEXT NOT NULL,
    dtype TEXT NOT NULL,
    reason TEXT,
    note TEXT
);

-- Повышения квалификации / обучение
CREATE TABLE IF NOT EXISTS training (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    tdate TEXT NOT NULL,
    program TEXT,
    result TEXT,
    note TEXT
);

-- Увольнения и уход на пенсию
CREATE TABLE IF NOT EXISTS terminations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    term_date TEXT NOT NULL,
    reason TEXT NOT NULL,
    basis TEXT,
    pension INTEGER DEFAULT 0,
    note TEXT
);

-- История должностей и окладов (для кадрового учёта)
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    hdate TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    note TEXT
);
"""


def get_db_path():
    """Файл БД хранится в пользовательской папке (C:/Users/.../HRPortal на Windows)."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    directory = os.path.join(base, APP_DIR_NAME)
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "hr_portal.db")


class Database:
    def __init__(self, path=None):
        self.path = path or get_db_path()
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- низкоуровневые операции ----------
    def query(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur.lastrowid

    def executemany(self, sql, seq):
        self.conn.executemany(sql, seq)
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # ---------- сотрудники ----------
    def add_employee(self, data):
        cols = ", ".join(data.keys())
        marks = ", ".join("?" for _ in data)
        return self.execute(
            f"INSERT INTO employees ({cols}) VALUES ({marks})", tuple(data.values())
        )

    def update_employee(self, emp_id, data):
        sets = ", ".join(f"{k} = ?" for k in data)
        self.execute(f"UPDATE employees SET {sets} WHERE id = ?",
                     tuple(data.values()) + (emp_id,))

    def get_employee(self, emp_id):
        return self.query_one("SELECT * FROM employees WHERE id = ?", (emp_id,))

    def list_employees(self, search="", statuses=("Работает",)):
        sql = ("SELECT e.*, p.title AS position_title, d.name AS department_name "
               "FROM employees e "
               "LEFT JOIN positions p ON p.id = e.position_id "
               "LEFT JOIN departments d ON d.id = e.department_id ")
        conds, params = [], []
        if statuses:
            conds.append("e.status IN (%s)" % ",".join("?" for _ in statuses))
            params += list(statuses)
        if search:
            s = f"%{search.lower()}%"
            conds.append("(lower(e.last_name) LIKE ? OR lower(e.first_name) LIKE ? "
                         "OR lower(p.title) LIKE ? OR lower(d.name) LIKE ?)")
            params += [s, s, s, s]
        if conds:
            sql += "WHERE " + " AND ".join(conds) + " "
        sql += "ORDER BY e.last_name, e.first_name"
        return self.query(sql, params)

    # ---------- справочники ----------
    def add_department(self, name):
        return self.execute("INSERT INTO departments (name) VALUES (?)", (name,))

    def list_departments(self):
        return self.query("SELECT * FROM departments ORDER BY name")

    def add_position(self, title, department_id=None, base_salary=0):
        return self.execute(
            "INSERT INTO positions (title, department_id, base_salary) VALUES (?,?,?)",
            (title, department_id, base_salary))

    def list_positions(self):
        return self.query(
            "SELECT p.*, d.name AS department_name FROM positions p "
            "LEFT JOIN departments d ON d.id = p.department_id ORDER BY p.title")

    # ---------- записи по сотруднику ----------
    _TABLES = {
        "events": "events", "vacations": "vacations", "sick": "sick_leaves",
        "trips": "business_trips", "disciplinary": "disciplinary",
        "training": "training", "terminations": "terminations",
        "history": "history",
    }

    def add_record(self, table, data):
        tbl = self._TABLES[table]
        cols = ", ".join(data.keys())
        marks = ", ".join("?" for _ in data)
        return self.execute(f"INSERT INTO {tbl} ({cols}) VALUES ({marks})",
                            tuple(data.values()))

    def list_records(self, table, employee_id=None):
        tbl = self._TABLES[table]
        if employee_id:
            return self.query(f"SELECT * FROM {tbl} WHERE employee_id=? "
                              f"ORDER BY rowid DESC", (employee_id,))
        return self.query(f"SELECT * FROM {tbl} ORDER BY rowid DESC")

    def delete_record(self, table, rec_id):
        tbl = self._TABLES[table]
        self.execute(f"DELETE FROM {tbl} WHERE id=?", (rec_id,))

    # ---------- учётная аналитика ----------
    def count_by_status(self):
        return self.query("SELECT status, COUNT(*) c FROM employees GROUP BY status")

    def count_by_department(self):
        return self.query(
            "SELECT d.name, COUNT(e.id) c FROM departments d "
            "LEFT JOIN employees e ON e.department_id=d.id AND e.status='Работает' "
            "GROUP BY d.id ORDER BY c DESC")

    def count_by_event_type(self):
        return self.query("SELECT event_type, COUNT(*) c FROM events "
                          "GROUP BY event_type ORDER BY c DESC")

    def avg_salary(self):
        r = self.query_one(
            "SELECT AVG(salary) a FROM employees WHERE status='Работает'")
        return (r["a"] or 0) if r else 0

    def total_payroll(self):
        r = self.query_one(
            "SELECT COALESCE(SUM(salary),0) s FROM employees WHERE status='Работает'")
        return r["s"] if r else 0
