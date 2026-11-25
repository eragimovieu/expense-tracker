"""SQL Server access for the expenses service.

DATABASE_URL looks like mssql://user:password@host:1433/database
(a password with special characters has to be URL-encoded).

On Azure the database is serverless and pauses after an hour without
connections. The first connection after that fails for up to about a minute
while it resumes (error 40613, or a 20002/20003 timeout from pymssql), so
connect() retries with a growing wait instead of failing straight away.
"""
import logging
import time
from urllib.parse import unquote, urlparse

import pymssql
from flask import current_app, g

log = logging.getLogger("db")

STARTUP_ATTEMPTS = 8  # about 1.5 to 2.5 minutes in total: enough for a resume
REQUEST_ATTEMPTS = 3  # a user is waiting, so give up sooner and answer 503


class DatabaseUnavailable(Exception):
    """Could not connect even after retrying."""


def parse_database_url(url):
    parts = urlparse(url)
    database = parts.path.lstrip("/")
    if parts.scheme != "mssql" or not parts.hostname or not database:
        raise ValueError("DATABASE_URL must look like mssql://user:password@host:1433/database")
    return {
        "server": parts.hostname,
        "port": str(parts.port or 1433),
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "database": database,
    }


def connect(url, attempts=REQUEST_ATTEMPTS):
    settings = parse_database_url(url)
    wait = 2
    for attempt in range(1, attempts + 1):
        try:
            return pymssql.connect(
                **settings,
                login_timeout=10,
                timeout=30,          # no single query may hang a request
                tds_version="7.4",   # needed for DATE columns to come back as dates
                as_dict=True,        # rows as dicts: row["category"]
            )
        except pymssql.Error as err:
            if attempt == attempts:
                message = f"no database connection after {attempts} attempts"
                raise DatabaseUnavailable(message) from err
            log.warning(
                "Database connection failed (attempt %d of %d), retrying in %ds: %s",
                attempt, attempts, wait, err,
            )
            time.sleep(wait)
            wait = min(wait * 2, 15)


def get_db():
    """This request's connection, opened the first time it's needed."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_URL"])
    return g.db


def close_db(exception=None):
    """Called by Flask at the end of every request."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def check_read_write(conn):
    """Used by /health. Reads a table, then takes a write lock on one row and
    rolls it back: that proves the login can read and write without changing
    anything."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS applied FROM schema_migrations")
    cursor.fetchone()
    cursor.execute("UPDATE TOP (1) schema_migrations SET applied_at = applied_at")
    conn.rollback()
