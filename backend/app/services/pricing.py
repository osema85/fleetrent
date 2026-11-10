"""All money calculations live here so they are consistent and unit-testable."""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import settings
from app.models.enums import CarCategory, InsuranceOption

CENT = Decimal("0.01")

INSURANCE_DAILY = {
    InsuranceOption.none: Decimal("0"),
    InsuranceOption.basic: Decimal("12"),
    InsuranceOption.full: Decimal("25"),
}
GPS_DAILY = Decimal("5")
CHILD_SEAT_DAILY = Decimal("4")
ADDITIONAL_DRIVER_DAILY = Decimal("8")

DEPOSIT_BY_CATEGORY = {
    CarCategory.economy: Decimal("200"),
    CarCategory.compact: Decimal("250"),
    CarCategory.midsize: Decimal("300"),
    CarCategory.suv: Decimal("400"),
    CarCategory.van: Decimal("400"),
    CarCategory.luxury: Decimal("1000"),
}


def money(value: Decimal | int | float) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def rental_days(start: datetime, end: datetime) -> int:
    """Every started 24h period counts as a day; minimum one day."""
    return max(1, math.ceil((end - start).total_seconds() / 86400))


def extras_daily(insurance: InsuranceOption, gps: bool, child_seat: bool, additional_driver: bool) -> Decimal:
    total = INSURANCE_DAILY[insurance]
    if gps:
        total += GPS_DAILY
    if child_seat:
        total += CHILD_SEAT_DAILY
    if additional_driver:
        total += ADDITIONAL_DRIVER_DAILY
    return total


def deposit_for(category: CarCategory, insurance: InsuranceOption) -> Decimal:
    deposit = DEPOSIT_BY_CATEGORY[category]
    if insurance == InsuranceOption.full:
        deposit = deposit / 2  # full cover halves the deposit
    return money(deposit)


@dataclass
class Quote:
    days: int
    daily_rate: Decimal
    base_amount: Decimal
    extras_amount: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal


def quote(
    daily_rate: Decimal,
    start: datetime,
    end: datetime,
    insurance: InsuranceOption,
    gps: bool,
    child_seat: bool,
    additional_driver: bool,
) -> Quote:
    days = rental_days(start, end)
    base = money(daily_rate * days)
    extras = money(extras_daily(insurance, gps, child_seat, additional_driver) * days)
    subtotal = base + extras
    tax = money(subtotal * settings.tax_rate)
    return Quote(days, money(daily_rate), base, extras, subtotal, tax, subtotal + tax)


@dataclass
class FinalCharges:
    base_amount: Decimal
    extras_amount: Decimal
    late_fee: Decimal
    mileage_fee: Decimal
    fuel_fee: Decimal
    damage_fee: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    late_days: int = 0
    extra_km: int = 0
    details: dict = field(default_factory=dict)

    @property
    def subtotal(self) -> Decimal:
        return (
            self.base_amount
            + self.extras_amount
            + self.late_fee
            + self.mileage_fee
            + self.fuel_fee
            + self.damage_fee
        )


def final_charges(
    *,
    daily_rate: Decimal,
    start_at: datetime,
    end_at: datetime,
    returned_at: datetime,
    insurance: InsuranceOption,
    gps: bool,
    child_seat: bool,
    additional_driver: bool,
    start_mileage: int,
    end_mileage: int,
    start_fuel: int,
    end_fuel: int,
    damage_fee: Decimal,
) -> FinalCharges:
    days = rental_days(start_at, end_at)
    per_day_extras = extras_daily(insurance, gps, child_seat, additional_driver)
    base = money(daily_rate * days)
    extras = money(per_day_extras * days)

    # Late return: each started day after the grace period, at a surcharge
    late_days = 0
    overdue = returned_at - end_at
    if overdue > timedelta(minutes=settings.late_grace_minutes):
        late_days = math.ceil(overdue.total_seconds() / 86400)
    late_fee = money((daily_rate + per_day_extras) * late_days * settings.late_day_multiplier)

    # Mileage above the included allowance
    driven = max(0, end_mileage - start_mileage)
    allowance = settings.km_allowance_per_day * (days + late_days)
    extra_km = max(0, driven - allowance)
    mileage_fee = money(Decimal(extra_km) * settings.extra_km_fee)

    # Fuel / battery returned lower than at pickup
    missing_fuel = max(0, start_fuel - end_fuel)
    fuel_fee = money(Decimal(missing_fuel) * settings.fuel_fee_per_percent)

    damage = money(damage_fee)
    subtotal = base + extras + late_fee + mileage_fee + fuel_fee + damage
    tax = money(subtotal * settings.tax_rate)
    return FinalCharges(
        base_amount=base,
        extras_amount=extras,
        late_fee=late_fee,
        mileage_fee=mileage_fee,
        fuel_fee=fuel_fee,
        damage_fee=damage,
        tax_amount=tax,
        total_amount=subtotal + tax,
        late_days=late_days,
        extra_km=extra_km,
        details={"driven_km": driven, "allowance_km": allowance, "missing_fuel_pct": missing_fuel},
    )
