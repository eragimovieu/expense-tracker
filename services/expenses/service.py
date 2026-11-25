"""Business logic of the expenses service.

This is the only code that reads or writes the expenses table. Every function
takes an open connection as its first argument: the routes pass the request's
connection, the tests pass one to a test database.
"""
from datetime import date

from utils import ValidationError, month_bounds, normalize_category, parse_amount, parse_month

MAX_DESCRIPTION_LENGTH = 200


def parse_spent_on(value):
    """Accept 'YYYY-MM-DD'. Empty means today; future dates are rejected."""
    if not value:
        return date.today().isoformat()
    try:
        day = date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValidationError("Date must look like 2026-10-03.") from None
    if day > date.today():
        raise ValidationError("Date can't be in the future.")
    return day.isoformat()


def iso_date(value):
    """pymssql gives DATE columns back as datetime.date; the API sends text."""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)[:10]


def to_expense(row):
    return {
        "id": row["id"],
        "amount_cents": row["amount_cents"],
        "category": row["category"],
        "description": row["description"],
        "spent_on": iso_date(row["spent_on"]),
    }


def add_expense(conn, amount, category, description="", spent_on=""):
    """Validate the input, insert one expense and return it with its new id."""
    amount_cents = parse_amount(amount)
    category = normalize_category(category)
    description = (description or "").strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(f"Description must be {MAX_DESCRIPTION_LENGTH} characters or less.")
    spent_on = parse_spent_on(spent_on)

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (amount_cents, category, description, spent_on) "
        "OUTPUT INSERTED.id VALUES (%s, %s, %s, %s)",
        (amount_cents, category, description, spent_on),
    )
    new_id = cursor.fetchone()["id"]
    conn.commit()
    return {
        "id": new_id,
        "amount_cents": amount_cents,
        "category": category,
        "description": description,
        "spent_on": spent_on,
    }


def list_expenses(conn, month):
    """All expenses in one month, newest first."""
    start, end = month_bounds(parse_month(month))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, amount_cents, category, description, spent_on FROM expenses "
        "WHERE spent_on >= %s AND spent_on < %s "
        "ORDER BY spent_on DESC, id DESC",
        (start, end),
    )
    return [to_expense(row) for row in cursor.fetchall()]


def delete_expense(conn, expense_id):
    """Return True if something was deleted, False if the id didn't exist."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    deleted = cursor.rowcount == 1
    conn.commit()
    return deleted


def totals_by_category(conn, month):
    """Total spent per category in one month, e.g. {'groceries': 4250}.

    This is what the budgets service asks for over HTTP
    (GET /api/expenses/totals), the only data that crosses the seam (ADR-6).
    """
    start, end = month_bounds(parse_month(month))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category, SUM(amount_cents) AS total FROM expenses "
        "WHERE spent_on >= %s AND spent_on < %s "
        "GROUP BY category ORDER BY category",
        (start, end),
    )
    return {row["category"]: row["total"] for row in cursor.fetchall()}


def known_categories(conn):
    """Every category used so far, for the suggestion list in the form."""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM expenses ORDER BY category")
    return [row["category"] for row in cursor.fetchall()]
