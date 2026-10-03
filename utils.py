"""Small helpers used by both domains. Nothing here touches the database or
keeps state, so when the domains become separate services each one can simply
keep its own copy of this file."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MAX_AMOUNT = Decimal("1000000")  # 1 million euros is clearly a typo
MAX_CATEGORY_LENGTH = 40


class ValidationError(ValueError):
    """Bad user input. Routes catch it and show the message to the user."""


def current_month():
    return datetime.now().strftime("%Y-%m")


def parse_month(value):
    """Return a 'YYYY-MM' string. Empty input means the current month."""
    if not value:
        return current_month()
    value = value.strip()
    if not MONTH_PATTERN.match(value):
        raise ValidationError("Month must look like 2026-10.")
    return value


def shift_month(month, delta):
    """shift_month('2026-01', -1) -> '2025-12'. Used for the < > month links."""
    year, mon = (int(part) for part in month.split("-"))
    index = year * 12 + (mon - 1) + delta  # months counted from year 0
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_label(month):
    """'2026-10' -> 'October 2026'."""
    return datetime.strptime(month, "%Y-%m").strftime("%B %Y")


def normalize_category(value):
    """'  Eating   Out ' -> 'eating out'. Both domains use this, which is how
    an expense and a budget end up with exactly the same category text."""
    cleaned = " ".join((value or "").split()).lower()
    if not cleaned:
        raise ValidationError("Category is required.")
    if len(cleaned) > MAX_CATEGORY_LENGTH:
        raise ValidationError(f"Category must be {MAX_CATEGORY_LENGTH} characters or less.")
    return cleaned


def parse_amount(value):
    """Turn what the user typed ('12.50', '12,5', '3') into integer cents."""
    text = str(value or "").strip().replace(",", ".")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValidationError("Amount must be a number, e.g. 12.50.") from None
    if not amount.is_finite() or amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    if amount > MAX_AMOUNT:
        raise ValidationError("Amount is too large.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValidationError("Amount can have at most 2 decimals.")
    return int(amount * 100)


def format_money(cents):
    """1250 -> '12.50', 123456 -> '1,234.56', -500 -> '-5.00'."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100:,}.{cents % 100:02d}"
