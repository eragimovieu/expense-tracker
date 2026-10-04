"""A few end-to-end smoke tests through Flask's test client. The real logic is
tested in test_expenses.py / test_budgets.py; these only check that the pages,
forms and JSON endpoints are wired up and that config comes from env vars."""
import pytest

from app import create_app
from config import load_config


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Point DATA_DIR at a temporary folder so tests never touch data/expenses.db
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    app = create_app()
    return app.test_client()


def test_config_comes_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("PORT", "9999")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    config = load_config()
    assert config["PORT"] == 9999
    assert config["HOST"] == "0.0.0.0"
    assert config["DATABASE"] == str(tmp_path / "expenses.db")


def test_startup_creates_the_database_file(client, tmp_path):
    assert (tmp_path / "expenses.db").exists()


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_home_redirects_to_expenses(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/expenses")


def test_add_expense_through_the_form(client):
    response = client.post(
        "/expenses",
        data={"amount": "12,50", "category": "Groceries", "spent_on": "2026-09-02", "month": "2026-09"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Expense added." in response.data
    assert b"12.50" in response.data

    totals = client.get("/api/expenses/totals?month=2026-09").get_json()
    assert totals == {"month": "2026-09", "totals": {"groceries": 1250}}


def test_bad_expense_shows_an_error_instead_of_crashing(client):
    response = client.post("/expenses", data={"amount": "abc", "category": "x"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Amount must be a number" in response.data


def test_delete_expense_through_the_form(client):
    client.post("/expenses", data={"amount": "3", "category": "coffee", "spent_on": "2026-09-01"})
    expense_id = client.get("/api/expenses?month=2026-09").get_json()["expenses"][0]["id"]

    response = client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)
    assert b"Expense deleted." in response.data
    assert client.get("/api/expenses?month=2026-09").get_json()["expenses"] == []


def test_budget_page_shows_status(client):
    client.post("/expenses", data={"amount": "90", "category": "groceries", "spent_on": "2026-09-02"})
    client.post("/budgets", data={"category": "groceries", "monthly_limit": "100"})

    page = client.get("/budgets?month=2026-09")
    assert b"status-warning" in page.data

    status = client.get("/api/budgets/status?month=2026-09").get_json()
    assert status["budgets"][0]["percent_used"] == 90


def test_bad_month_in_api_returns_400(client):
    assert client.get("/api/budgets/status?month=sept").status_code == 400
    assert client.get("/api/expenses?month=sept").status_code == 400
