import os
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS team (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lab1_answers (
    slug TEXT PRIMARY KEY,
    score INTEGER,
    route TEXT
);
CREATE TABLE IF NOT EXISTS lab2_answers (
    card TEXT PRIMARY KEY,
    bucket TEXT,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS lab3_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status INTEGER NOT NULL,
    booking_id INTEGER
);
CREATE TABLE IF NOT EXISTS lab3_report (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    body TEXT NOT NULL,
    updated TEXT NOT NULL
);
"""

TABLES = ("team", "lab1_answers", "lab2_answers", "lab3_requests", "lab3_report")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app):
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    with sqlite3.connect(app.config["DATABASE"]) as conn:
        conn.executescript(SCHEMA)
    app.teardown_appcontext(close_db)


def reset_all():
    conn = get_db()
    for table in TABLES:
        conn.execute(f"DELETE FROM {table}")  # table names are constants above
    conn.commit()
