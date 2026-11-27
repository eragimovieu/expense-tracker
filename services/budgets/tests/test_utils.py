import pytest

from utils import ValidationError, normalize_category, parse_amount, parse_month


@pytest.mark.parametrize(
    ("typed", "cents"),
    [("300", 30000), ("12,5", 1250), ("0.29", 29), ("0.01", 1), ("1000000", 100000000)],
)
def test_parse_amount(typed, cents):
    assert parse_amount(typed) == cents


@pytest.mark.parametrize("typed", ["", "abc", "0", "-3", "1.234", "1000000.01", "nan", "inf"])
def test_parse_amount_rejects(typed):
    with pytest.raises(ValidationError):
        parse_amount(typed)


def test_normalize_category():
    assert normalize_category("  Eating   Out ") == "eating out"
    with pytest.raises(ValidationError):
        normalize_category("   ")
    with pytest.raises(ValidationError):
        normalize_category("x" * 41)


def test_parse_month():
    assert parse_month("2026-11") == "2026-11"
    assert len(parse_month("")) == 7  # current month
    with pytest.raises(ValidationError):
        parse_month("2026-13")
