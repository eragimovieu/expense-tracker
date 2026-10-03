"""SQLite helpers. One database file for the whole app; its path comes from
config (DATA_DIR/expenses.db). Both domains get their connection from here."""
import os
import sqlite3

from flask import current_app, g

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # lets me write row["category"] instead of row[2]
    return conn


def init_db(conn):
    """Create the tables if they don't exist yet. Safe to run on every start."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


def get_db():
    """Return this request's connection, opening it the first time it's needed."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(exception=None):
    """Called by Flask at the end of every request."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
