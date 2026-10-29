from datetime import date
from decimal import Decimal

from app.services.rules import day_bounds, mask_id, mask_phone, price_total


def test_pricing_uses_decimal_and_handles_empty_and_zero():
    assert price_total([(Decimal("0.10"), 3), (Decimal("12.50"), 2)]) == Decimal("25.30")
    assert price_total([]) == Decimal("0.00")
    assert price_total([(Decimal("0"), 3), (Decimal("1.2"), 0)]) == Decimal("0.00")


def test_business_day_uses_china_midnight():
    start, end = day_bounds(date(2026, 10, 29))
    assert start.isoformat() == "2026-10-28T16:00:00+00:00"
    assert (end - start).total_seconds() == 86400


def test_identity_redaction_is_idempotent():
    assert mask_id("110101200001011234") == "**************1234"
    assert mask_id(mask_id("110101200001011234")) == "**************1234"
    assert mask_phone("13812345678") == "138****5678"
    assert mask_phone(mask_phone("13812345678")) == "138****5678"
