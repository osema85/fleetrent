import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import (
    InsuranceOption,
    PaymentKind,
    PaymentMethod,
    RentalStatus,
    ReservationStatus,
)
from app.schemas.common import InputModel, LongText, Mileage, Money, OutputModel, Percent, PositiveMoney
from app.schemas.customer import CustomerBrief
from app.schemas.fleet import CarBrief


class Extras(InputModel):
    insurance: InsuranceOption = InsuranceOption.none
    gps: bool = False
    child_seat: bool = False
    additional_driver: bool = False


class Period(InputModel):
    start_at: AwareDatetime
    end_at: AwareDatetime

    @model_validator(mode="after")
    def check_period(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class QuoteRequest(Period, Extras):
    car_id: uuid.UUID


class QuoteOut(OutputModel):
    days: int
    daily_rate: Decimal
    base_amount: Decimal
    extras_amount: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    deposit: Decimal
    currency: str


class ReservationCreate(Period, Extras):
    car_id: uuid.UUID
    customer_id: uuid.UUID | None = None  # required for staff, ignored for customers
    pickup_branch_id: uuid.UUID | None = None
    return_branch_id: uuid.UUID | None = None
    notes: LongText | None = None


class CancelRequest(InputModel):
    reason: str = Field(default="", max_length=255)


class ReservationOut(OutputModel):
    id: uuid.UUID
    code: str
    status: ReservationStatus
    customer_id: uuid.UUID
    customer: CustomerBrief
    car_id: uuid.UUID
    car: CarBrief
    pickup_branch_id: uuid.UUID | None
    return_branch_id: uuid.UUID | None
    start_at: datetime
    end_at: datetime
    daily_rate: Decimal
    insurance: InsuranceOption
    gps: bool
    child_seat: bool
    additional_driver: bool
    estimated_total: Decimal
    deposit_amount: Decimal
    notes: str | None
    cancel_reason: str | None
    created_at: datetime


# ------------------------------------------------------------------ rentals


class CheckoutRequest(InputModel):
    reservation_id: uuid.UUID
    start_mileage: Mileage
    start_fuel_level: Percent
    notes: LongText | None = None


class CheckinRequest(InputModel):
    end_mileage: Mileage
    end_fuel_level: Percent
    returned_at: AwareDatetime | None = None
    damage_notes: LongText | None = None
    damage_fee: Money = Decimal("0")
    send_to_maintenance: bool = False


class RentalOut(OutputModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    status: RentalStatus
    checked_out_at: datetime
    start_mileage: int
    start_fuel_level: int
    checkout_notes: str | None
    checked_in_at: datetime | None
    end_mileage: int | None
    end_fuel_level: int | None
    damage_notes: str | None
    base_amount: Decimal | None
    extras_amount: Decimal | None
    late_fee: Decimal | None
    mileage_fee: Decimal | None
    fuel_fee: Decimal | None
    damage_fee: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None


class RentalListItem(RentalOut):
    reservation: ReservationOut


# ------------------------------------------------------------------ payments


class PaymentCreate(InputModel):
    reservation_id: uuid.UUID
    amount: PositiveMoney
    method: PaymentMethod
    kind: PaymentKind = PaymentKind.payment
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=255)


class PaymentOut(OutputModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    kind: PaymentKind
    reference: str | None
    notes: str | None
    created_at: datetime


class Balance(OutputModel):
    total_due: Decimal
    paid: Decimal
    balance: Decimal
    deposit_required: Decimal
    deposit_held: Decimal
    is_final: bool


class LineItem(OutputModel):
    label: str
    amount: Decimal


class InvoiceOut(OutputModel):
    company_name: str
    currency: str
    invoice_number: str
    issued_at: datetime
    reservation: ReservationOut
    rental: RentalOut | None
    line_items: list[LineItem]
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    payments: list[PaymentOut]
    balance: Balance
