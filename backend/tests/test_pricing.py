from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.enums import CarCategory, InsuranceOption
from app.services import pricing

START = datetime(2026, 1, 10, 10, 0, tzinfo=UTC)


def test_rental_days_counts_started_days():
    assert pricing.rental_days(START, START + timedelta(hours=2)) == 1
    assert pricing.rental_days(START, START + timedelta(days=1)) == 1
    assert pricing.rental_days(START, START + timedelta(days=1, minutes=1)) == 2


def test_quote_with_extras_and_tax():
    q = pricing.quote(Decimal("50"), START, START + timedelta(days=3), InsuranceOption.basic, True, False, False)
    assert q.days == 3
    assert q.base_amount == Decimal("150.00")
    assert q.extras_amount == Decimal("51.00")  # (12 + 5) * 3
    assert q.tax_amount == Decimal("40.20")
    assert q.total == Decimal("241.20")


def test_full_insurance_halves_deposit():
    assert pricing.deposit_for(CarCategory.luxury, InsuranceOption.full) == Decimal("500.00")
    assert pricing.deposit_for(CarCategory.luxury, InsuranceOption.none) == Decimal("1000.00")


def _final(**overrides):
    args = dict(
        daily_rate=Decimal("40"), start_at=START, end_at=START + timedelta(days=2), returned_at=START + timedelta(days=2),
        insurance=InsuranceOption.none, gps=False, child_seat=False, additional_driver=False,
        start_mileage=1000, end_mileage=1200, start_fuel=100, end_fuel=100, damage_fee=Decimal("0"),
    )
    args.update(overrides)
    return pricing.final_charges(**args)


def test_on_time_return_has_no_fees():
    c = _final()
    assert (c.late_fee, c.mileage_fee, c.fuel_fee) == (0, 0, 0)
    assert c.total_amount == Decimal("96.00")


def test_return_within_grace_period_is_not_late():
    assert _final(returned_at=START + timedelta(days=2, minutes=59)).late_fee == 0


def test_late_return_charges_surcharged_day():
    c = _final(returned_at=START + timedelta(days=2, hours=3))
    assert c.late_days == 1
    assert c.late_fee == Decimal("50.00")  # 40 * 1.25


def test_mileage_and_fuel_fees():
    c = _final(end_mileage=1000 + 700, end_fuel=80)  # allowance 600 km
    assert c.extra_km == 100
    assert c.mileage_fee == Decimal("30.00")
    assert c.fuel_fee == Decimal("30.00")
