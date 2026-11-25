"""Business logic of the budgets service.

This is the only code that reads or writes the budgets table. Spending comes
in as a {category: cents} dict that the route got from the expenses service
(expenses_client.py). Nothing in this file makes HTTP calls, so the rules can
be tested with a plain dict.
"""
from utils import normalize_category, parse_amount

WARNING_RATIO = 0.8  # a budget turns "warning" once 80% of it is used


def set_budget(conn, category, monthly_limit):
    """Create a budget for a category, or change the limit if it exists."""
    category = normalize_category(category)
    limit_cents = parse_amount(monthly_limit)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE budgets SET monthly_limit_cents = %s WHERE category = %s",
        (limit_cents, category),
    )
    if cursor.rowcount == 0:
        cursor.execute(
            "INSERT INTO budgets (category, monthly_limit_cents) VALUES (%s, %s)",
            (category, limit_cents),
        )
    conn.commit()
    return {"category": category, "monthly_limit_cents": limit_cents}


def list_budgets(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, monthly_limit_cents FROM budgets ORDER BY category")
    return [dict(row) for row in cursor.fetchall()]


def delete_budget(conn, budget_id):
    """Return True if something was deleted, False if the id didn't exist."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budgets WHERE id = %s", (budget_id,))
    deleted = cursor.rowcount == 1
    conn.commit()
    return deleted


def classify(spent_cents, limit_cents):
    """'ok' below 80%, 'warning' from 80% up to exactly the limit, 'over' above it."""
    if spent_cents > limit_cents:
        return "over"
    if spent_cents >= limit_cents * WARNING_RATIO:
        return "warning"
    return "ok"


def budget_status(budgets, totals):
    """One row per budget: limit, spent, remaining, percentage used and status.
    A category with no spending this month counts as 0."""
    rows = []
    for budget in budgets:
        limit_cents = budget["monthly_limit_cents"]
        spent_cents = totals.get(budget["category"], 0)
        rows.append(
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
    return rows


def limits_only(budgets):
    """What the user gets when the expenses service can't be reached: the
    limits, which are this service's own data, with spending left empty."""
    return [
        {
            "id": budget["id"],
            "category": budget["category"],
            "limit_cents": budget["monthly_limit_cents"],
            "spent_cents": None,
            "remaining_cents": None,
            "percent_used": None,
            "status": "unknown",
        }
        for budget in budgets
    ]


def unbudgeted_spending(budgets, totals):
    """Categories with spending this month but no budget, e.g. {'taxi': 1200}."""
    budgeted = {budget["category"] for budget in budgets}
    return {category: cents for category, cents in totals.items() if category not in budgeted}


def status_report(conn, month, totals):
    """Everything the budgets page shows for one month. totals is None when
    the expenses service didn't answer (ADR-6)."""
    budgets = list_budgets(conn)
    if totals is None:
        return {
            "month": month,
            "spending_available": False,
            "budgets": limits_only(budgets),
            "unbudgeted": {},
        }
    return {
        "month": month,
        "spending_available": True,
        "budgets": budget_status(budgets, totals),
        "unbudgeted": unbudgeted_spending(budgets, totals),
    }
