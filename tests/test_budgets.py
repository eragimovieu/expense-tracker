import pytest

from budgets import service
from expenses import service as expenses_service
from utils import ValidationError


def test_set_budget_creates_one_per_category(conn):
    service.set_budget(conn, " Groceries ", "300")

    assert service.list_budgets(conn) == [
        {"id": 1, "category": "groceries", "monthly_limit_cents": 30000}
    ]


def test_set_budget_again_updates_the_limit(conn):
    service.set_budget(conn, "groceries", "300")
    service.set_budget(conn, "GROCERIES", "250.50")

    budgets = service.list_budgets(conn)
    assert len(budgets) == 1
    assert budgets[0]["monthly_limit_cents"] == 25050


@pytest.mark.parametrize("category, limit", [("", "100"), ("food", "0"), ("food", "lots")])
def test_set_budget_rejects_bad_input(conn, category, limit):
    with pytest.raises(ValidationError):
        service.set_budget(conn, category, limit)
    assert service.list_budgets(conn) == []


def test_delete_budget(conn):
    service.set_budget(conn, "coffee", "20")
    budget_id = service.list_budgets(conn)[0]["id"]

    assert service.delete_budget(conn, budget_id) is True
    assert service.list_budgets(conn) == []
    assert service.delete_budget(conn, budget_id) is False


@pytest.mark.parametrize(
    "spent, limit, expected",
    [
        (0, 10000, "ok"),
        (7999, 10000, "ok"),
        (8000, 10000, "warning"),  # exactly 80%
        (10000, 10000, "warning"),  # exactly at the limit is not over yet
        (10001, 10000, "over"),
    ],
)
def test_classify_thresholds(spent, limit, expected):
    assert service.classify(spent, limit) == expected


def test_budget_status_combines_budgets_with_that_months_spending(conn):
    service.set_budget(conn, "groceries", "100")
    service.set_budget(conn, "coffee", "20")
    service.set_budget(conn, "gym", "30")
    expenses_service.add_expense(conn, "85", "groceries", "", "2026-09-05")
    expenses_service.add_expense(conn, "25", "coffee", "", "2026-09-06")
    expenses_service.add_expense(conn, "500", "coffee", "", "2026-08-06")  # other month

    status = {row["category"]: row for row in service.budget_status(conn, "2026-09")}

    assert status["groceries"]["spent_cents"] == 8500
    assert status["groceries"]["remaining_cents"] == 1500
    assert status["groceries"]["percent_used"] == 85
    assert status["groceries"]["status"] == "warning"

    assert status["coffee"]["status"] == "over"
    assert status["coffee"]["remaining_cents"] == -500

    assert status["gym"]["spent_cents"] == 0  # no expenses yet
    assert status["gym"]["status"] == "ok"


def test_budget_status_with_no_budgets_is_empty(conn):
    expenses_service.add_expense(conn, "5", "coffee", "", "2026-09-01")
    assert service.budget_status(conn, "2026-09") == []


def test_budget_status_rejects_bad_month(conn):
    with pytest.raises(ValidationError):
        service.budget_status(conn, "September")
