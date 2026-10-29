from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal

CHINA = timezone(timedelta(hours=8))


def business_date() -> date:
    return datetime.now(CHINA).date()


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, CHINA).astimezone(UTC)
    return start, start + timedelta(days=1)


def price_total(items) -> Decimal:
    return sum((price * quantity for price, quantity in items), Decimal("0.00")).quantize(
        Decimal("0.01")
    )


def mask_id(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return "*" * max(4, len(value) - 4) + value[-4:]


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value[:3] + "****" + value[-4:] if len(value) >= 7 else "****"
