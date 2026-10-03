import pytest

from utils import (
    ValidationError,
    format_money,
    month_label,
    normalize_category,
    parse_amount,
    parse_month,
    shift_month,
)


@pytest.mark.parametrize(
    "typed, cents",
    [("12.50", 1250), ("12,5", 1250), ("3", 300), (" 0.01 ", 1), ("1000000", 100000000)],
)
def test_parse_amount_accepts_normal_input(typed, cents):
    assert parse_amount(typed) == cents


@pytest.mark.parametrize("typed", ["", "abc", "0", "-5", "12.345", "1000000.01", "nan", "inf", None])
def test_parse_amount_rejects_bad_input(typed):
    with pytest.raises(ValidationError):
        parse_amount(typed)


def test_parse_amount_avoids_float_rounding():
    # float("0.29") * 100 is 28.999999999999996, which int() would turn into 28
    assert parse_amount("0.29") == 29


def test_normalize_category_trims_and_lowercases():
    assert normalize_category("  Eating   Out ") == "eating out"


@pytest.mark.parametrize("bad", ["", "   ", None, "x" * 41])
def test_normalize_category_rejects_empty_or_long(bad):
    with pytest.raises(ValidationError):
        normalize_category(bad)


def test_parse_month_defaults_to_current_month():
    assert len(parse_month("")) == 7
    assert parse_month(None) == parse_month("")


@pytest.mark.parametrize("bad", ["2026-13", "2026-1", "October", "2026/10"])
def test_parse_month_rejects_bad_format(bad):
    with pytest.raises(ValidationError):
        parse_month(bad)


def test_shift_month_crosses_year_boundaries():
    assert shift_month("2026-01", -1) == "2025-12"
    assert shift_month("2026-12", 1) == "2027-01"
    assert shift_month("2026-10", 0) == "2026-10"


def test_month_label():
    assert month_label("2026-10") == "October 2026"


def test_format_money():
    assert format_money(1250) == "12.50"
    assert format_money(123456) == "1,234.56"
    assert format_money(5) == "0.05"
    assert format_money(-500) == "-5.00"
