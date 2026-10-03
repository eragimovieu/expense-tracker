from datetime import date, timedelta

import pytest

from expenses import service
from utils import ValidationError

# Fixed dates are in September 2026 so they are always in the past.


def test_add_expense_stores_cents_and_clean_category(conn):
    expense_id = service.add_expense(conn, "12.50", "  Groceries ", "Mercadona", "2026-09-02")

    rows = service.list_expenses(conn, "2026-09")
    assert rows == [
        {
            "id": expense_id,
            "amount_cents": 1250,
            "category": "groceries",
            "description": "Mercadona",
            "spent_on": "2026-09-02",
        }
    ]


def test_add_expense_without_date_uses_today(conn):
    service.add_expense(conn, "3", "coffee")
    today = date.today()
    rows = service.list_expenses(conn, today.strftime("%Y-%m"))
    assert rows[0]["spent_on"] == today.isoformat()


def test_add_expense_rejects_future_date(conn):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError, match="future"):
        service.add_expense(conn, "3", "coffee", spent_on=tomorrow)


@pytest.mark.parametrize("bad_date", ["03/09/2026", "2026-02-30", "yesterday"])
def test_add_expense_rejects_bad_dates(conn, bad_date):
    with pytest.raises(ValidationError):
        service.add_expense(conn, "3", "coffee", spent_on=bad_date)


def test_add_expense_rejects_long_description(conn):
    with pytest.raises(ValidationError):
        service.add_expense(conn, "3", "coffee", "x" * 201, "2026-09-01")


def test_invalid_expense_is_not_saved(conn):
    with pytest.raises(ValidationError):
        service.add_expense(conn, "-4", "coffee", "", "2026-09-01")
    assert service.list_expenses(conn, "2026-09") == []


def test_list_expenses_only_returns_that_month_newest_first(conn):
    service.add_expense(conn, "10", "rent", "", "2026-08-31")
    service.add_expense(conn, "5", "coffee", "", "2026-09-01")
    service.add_expense(conn, "7", "coffee", "", "2026-09-15")

    rows = service.list_expenses(conn, "2026-09")
    assert [row["spent_on"] for row in rows] == ["2026-09-15", "2026-09-01"]


def test_delete_expense(conn):
    expense_id = service.add_expense(conn, "5", "coffee", "", "2026-09-01")

    assert service.delete_expense(conn, expense_id) is True
    assert service.list_expenses(conn, "2026-09") == []
    assert service.delete_expense(conn, expense_id) is False  # already gone


def test_totals_by_category_sums_one_month(conn):
    service.add_expense(conn, "10.00", "groceries", "", "2026-09-01")
    service.add_expense(conn, "2.50", "Groceries", "", "2026-09-20")
    service.add_expense(conn, "4", "coffee", "", "2026-09-03")
    service.add_expense(conn, "99", "groceries", "", "2026-08-28")  # other month

    assert service.totals_by_category(conn, "2026-09") == {"coffee": 400, "groceries": 1250}


def test_totals_by_category_empty_month(conn):
    assert service.totals_by_category(conn, "2026-09") == {}


def test_known_categories_has_no_duplicates(conn):
    service.add_expense(conn, "1", "Coffee", "", "2026-09-01")
    service.add_expense(conn, "1", "coffee", "", "2026-09-02")
    service.add_expense(conn, "1", "bus", "", "2026-09-02")

    assert service.known_categories(conn) == ["bus", "coffee"]
