"""Business logic for the budgets domain.

This is the only code that reads or writes the `budgets` table. It never
queries the `expenses` table: spending comes from
expenses.service.totals_by_category(), the one seam between the domains (ADR-2).
"""
from expenses import service as expenses_service
from utils import normalize_category, parse_amount, parse_month

WARNING_RATIO = 0.8  # a budget turns "warning" once 80% of it is used


def set_budget(conn, category, monthly_limit):
    """Create a budget for a category, or update the limit if one exists."""
    category = normalize_category(category)
    limit_cents = parse_amount(monthly_limit)
    conn.execute(
        "INSERT INTO budgets (category, monthly_limit_cents) VALUES (?, ?) "
        "ON CONFLICT(category) DO UPDATE SET monthly_limit_cents = excluded.monthly_limit_cents",
        (category, limit_cents),
    )
    conn.commit()
    return category


def list_budgets(conn):
    rows = conn.execute(
        "SELECT id, category, monthly_limit_cents FROM budgets ORDER BY category"
    ).fetchall()
    return [dict(row) for row in rows]


def delete_budget(conn, budget_id):
    """Return True if something was deleted, False if the id didn't exist."""
    cursor = conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
    conn.commit()
    return cursor.rowcount == 1


def classify(spent_cents, limit_cents):
    """'ok' below 80%, 'warning' from 80% up to exactly the limit, 'over' above it."""
    if spent_cents > limit_cents:
        return "over"
    if spent_cents >= limit_cents * WARNING_RATIO:
        return "warning"
    return "ok"


def budget_status(conn, month):
    """One row per budget for the given month: limit, spent, remaining,
    percentage used and status. Categories with no spending count as 0."""
    month = parse_month(month)
    spent_by_category = expenses_service.totals_by_category(conn, month)

    report = []
    for budget in list_budgets(conn):
        limit_cents = budget["monthly_limit_cents"]
        spent_cents = spent_by_category.get(budget["category"], 0)
        report.append(
            {
                "id": budget["id"],
                "category": budget["category"],
                "limit_cents": limit_cents,
                "spent_cents": spent_cents,
                "remaining_cents": limit_cents - spent_cents,
                "percent_used": round(spent_cents * 100 / limit_cents),
                "status": classify(spent_cents, limit_cents),
            }
        )
    return report
