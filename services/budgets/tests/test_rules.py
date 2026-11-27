"""The budget rules, tested with plain dicts: no database and no expenses
service needed, because service.py gets the spending passed in."""
import pytest

import service


@pytest.mark.parametrize(
    ("spent", "limit", "expected"),
    [
        (0, 10000, "ok"),
        (7999, 10000, "ok"),
        (8000, 10000, "warning"),  # exactly 80%
        (10000, 10000, "warning"),  # exactly at the limit is not over yet
        (10001, 10000, "over"),  # one cent over
    ],
)
def test_classify_edges(spent, limit, expected):
    assert service.classify(spent, limit) == expected


BUDGETS = [
    {"id": 1, "category": "groceries", "monthly_limit_cents": 30000},
    {"id": 2, "category": "rent", "monthly_limit_cents": 50000},
]


def test_budget_status_rows():
    rows = service.budget_status(BUDGETS, {"groceries": 27000, "taxi": 1200})
    groceries, rent = rows
    assert groceries["spent_cents"] == 27000
    assert groceries["remaining_cents"] == 3000
    assert groceries["percent_used"] == 90
    assert groceries["status"] == "warning"
    # no spending in a budgeted category counts as 0
    assert rent["spent_cents"] == 0
    assert rent["status"] == "ok"


def test_over_budget_has_negative_remaining():
    (row,) = service.budget_status(BUDGETS[:1], {"groceries": 31000})
    assert row["status"] == "over"
    assert row["remaining_cents"] == -1000
    assert row["percent_used"] == 103


def test_unbudgeted_spending_lists_only_categories_without_a_budget():
    totals = {"groceries": 100, "taxi": 1200, "coffee": 350}
    assert service.unbudgeted_spending(BUDGETS, totals) == {"taxi": 1200, "coffee": 350}


def test_limits_only_when_spending_is_unavailable():
    rows = service.limits_only(BUDGETS)
    assert [row["status"] for row in rows] == ["unknown", "unknown"]
    assert rows[0]["limit_cents"] == 30000
    assert rows[0]["spent_cents"] is None
    assert rows[0]["percent_used"] is None
