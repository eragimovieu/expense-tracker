"""Business logic for the expenses domain.

This is the only code that reads or writes the `expenses` table. Every function
takes an open SQLite connection as its first argument: the routes pass the
request's connection, and the tests pass an in-memory database.
"""
from datetime import date

from utils import ValidationError, normalize_category, parse_amount, parse_month

MAX_DESCRIPTION_LENGTH = 200


def parse_spent_on(value):
    """Accept 'YYYY-MM-DD'. Empty means today; future dates are rejected."""
    if not value:
        return date.today().isoformat()
    try:
        day = date.fromisoformat(value.strip())
    except ValueError:
        raise ValidationError("Date must look like 2026-10-03.") from None
    if day > date.today():
        raise ValidationError("Date can't be in the future.")
    return day.isoformat()


def add_expense(conn, amount, category, description="", spent_on=""):
    """Validate the input, insert one expense and return its new id."""
    amount_cents = parse_amount(amount)
    category = normalize_category(category)
    description = (description or "").strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(f"Description must be {MAX_DESCRIPTION_LENGTH} characters or less.")
    spent_on = parse_spent_on(spent_on)

    cursor = conn.execute(
        "INSERT INTO expenses (amount_cents, category, description, spent_on) "
        "VALUES (?, ?, ?, ?)",
        (amount_cents, category, description, spent_on),
    )
    conn.commit()
    return cursor.lastrowid


def list_expenses(conn, month):
    """All expenses in one month, newest first, as plain dicts."""
    month = parse_month(month)
    rows = conn.execute(
        "SELECT id, amount_cents, category, description, spent_on FROM expenses "
        "WHERE substr(spent_on, 1, 7) = ? "
        "ORDER BY spent_on DESC, id DESC",
        (month,),
    ).fetchall()
    return [dict(row) for row in rows]


def delete_expense(conn, expense_id):
    """Return True if something was deleted, False if the id didn't exist."""
    cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    return cursor.rowcount == 1


def totals_by_category(conn, month):
    """Total spent per category in one month, e.g. {'groceries': 4250}.

    This is the seam between the two domains (ADR-2): the budgets domain gets
    spending data only through this function, never by querying the table.
    """
    month = parse_month(month)
    rows = conn.execute(
        "SELECT category, SUM(amount_cents) AS total FROM expenses "
        "WHERE substr(spent_on, 1, 7) = ? "
        "GROUP BY category ORDER BY category",
        (month,),
    ).fetchall()
    return {row["category"]: row["total"] for row in rows}


def known_categories(conn):
    """Every category used so far, for the suggestion list in the form."""
    rows = conn.execute("SELECT DISTINCT category FROM expenses ORDER BY category").fetchall()
    return [row["category"] for row in rows]
