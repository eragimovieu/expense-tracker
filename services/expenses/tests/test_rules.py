"""Expense rules that don't need a database."""
from datetime import date, timedelta

import pytest

import service
from utils import ValidationError


def test_spent_on_defaults_to_today():
    assert service.parse_spent_on("") == date.today().isoformat()


def test_spent_on_rejects_future_and_bad_dates():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        service.parse_spent_on(tomorrow)
    with pytest.raises(ValidationError):
        service.parse_spent_on("25/11/2026")


def test_iso_date_handles_dates_and_text():
    assert service.iso_date(date(2026, 11, 3)) == "2026-11-03"
    assert service.iso_date("2026-11-03 00:00:00") == "2026-11-03"


def test_description_too_long_is_rejected_before_any_sql():
    with pytest.raises(ValidationError):
        service.add_expense(None, "5", "coffee", "x" * 201)
