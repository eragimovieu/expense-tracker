"""Applies the numbered .sql files in migrations/ in order, each one once.

The file names that were applied are stored in schema_migrations, so a second
start applies nothing. Each file runs in its own transaction: if it fails,
it is rolled back, not recorded, and the service doesn't start.
An applied file is never edited; a fix goes into a new file (ADR-7).
"""
import logging
import os
import re

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
FILE_NAME = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")  # e.g. 001_init.sql
BATCH_SEPARATOR = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)

log = logging.getLogger("migrate")

CREATE_HISTORY_TABLE = """
IF OBJECT_ID('schema_migrations', 'U') IS NULL
    CREATE TABLE schema_migrations (
        version    NVARCHAR(100) NOT NULL PRIMARY KEY,
        applied_at DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
    );
"""


def migration_files(folder=MIGRATIONS_DIR):
    """All migration files, sorted, so 002 always runs after 001."""
    return sorted(name for name in os.listdir(folder) if FILE_NAME.match(name))


def split_batches(sql):
    """Split a file on GO lines, like sqlcmd does. Needed when a statement has
    to see a column that an earlier statement in the same file added."""
    return [batch.strip() for batch in BATCH_SEPARATOR.split(sql) if batch.strip()]


def run_migrations(conn, folder=MIGRATIONS_DIR):
    """Apply what's missing and return the names that were applied."""
    cursor = conn.cursor()
    cursor.execute(CREATE_HISTORY_TABLE)
    conn.commit()

    cursor.execute("SELECT version FROM schema_migrations")
    applied = {row["version"] for row in cursor.fetchall()}
    pending = [name for name in migration_files(folder) if name not in applied]

    for name in pending:
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            sql = f.read()
        try:
            for batch in split_batches(sql):
                cursor.execute(batch)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (name,))
            conn.commit()
        except Exception:
            conn.rollback()
            log.error("Migration %s failed and was rolled back", name)
            raise
        log.info("Applied migration %s", name)

    if not pending:
        log.info("Database schema is up to date (%d migrations applied before)", len(applied))
    return pending
