"""Input helpers, copied from the A1 utils.py when the app was split (ADR-2
said this copy would happen). Only what the expenses service uses is kept;
the money and month formatting moved to the UI."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MAX_AMOUNT = Decimal("1000000")  # 1 million euros is clearly a typo
MAX_CATEGORY_LENGTH = 40


class ValidationError(ValueError):
    """Bad user input. The routes turn it into a 400 with the message."""


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
    """shift_month('2026-01', -1) -> '2025-12'."""
    year, mon = (int(part) for part in month.split("-"))
    index = year * 12 + (mon - 1) + delta  # months counted from year 0
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_bounds(month):
    """'2026-11' -> ('2026-11-01', '2026-12-01'): first day of the month and
    first day of the next one, for WHERE spent_on >= start AND spent_on < end."""
    return f"{month}-01", f"{shift_month(month, 1)}-01"


def normalize_category(value):
    """'  Eating   Out ' -> 'eating out'. The budgets service does exactly the
    same, which is how an expense and a budget end up with the same text."""
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
