import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    InsuranceOption,
    PaymentKind,
    PaymentMethod,
    RentalStatus,
    ReservationStatus,
    enum_column,
)


class Reservation(TimestampMixin, Base):
    """A booking of one car for a time window.

    The database additionally enforces (migration 0001) an exclusion constraint that makes
    it impossible for two pending/confirmed/active reservations of the same car to overlap.
    """

    __tablename__ = "reservations"
    __table_args__ = (CheckConstraint("end_at > start_at", name="ck_reservations_period"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(12), unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    car_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cars.id", ondelete="RESTRICT"), index=True)
    pickup_branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    return_branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReservationStatus] = mapped_column(
        enum_column(ReservationStatus), default=ReservationStatus.pending, index=True
    )
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    insurance: Mapped[InsuranceOption] = mapped_column(enum_column(InsuranceOption), default=InsuranceOption.none)
    gps: Mapped[bool] = mapped_column(Boolean, default=False)
    child_seat: Mapped[bool] = mapped_column(Boolean, default=False)
    additional_driver: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    car = relationship("Car")
    customer = relationship("Customer")
    pickup_branch = relationship("Branch", foreign_keys=[pickup_branch_id])
    return_branch = relationship("Branch", foreign_keys=[return_branch_id])
    rental = relationship("Rental", back_populates="reservation", uselist=False)
    payments = relationship("Payment", back_populates="reservation", order_by="Payment.created_at")


class Rental(TimestampMixin, Base):
    """The rental contract: created at vehicle check-out, closed at check-in."""

    __tablename__ = "rentals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id", ondelete="RESTRICT"), unique=True
    )
    status: Mapped[RentalStatus] = mapped_column(enum_column(RentalStatus), default=RentalStatus.open, index=True)
    checked_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_out_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    start_mileage: Mapped[int] = mapped_column(Integer)
    start_fuel_level: Mapped[int] = mapped_column(Integer)
    checkout_notes: Mapped[str | None] = mapped_column(Text)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_in_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    end_mileage: Mapped[int | None] = mapped_column(Integer)
    end_fuel_level: Mapped[int | None] = mapped_column(Integer)
    damage_notes: Mapped[str | None] = mapped_column(Text)
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    extras_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    late_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    mileage_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    fuel_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    damage_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    reservation = relationship("Reservation", back_populates="rental")


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payments_amount_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservations.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    method: Mapped[PaymentMethod] = mapped_column(enum_column(PaymentMethod))
    kind: Mapped[PaymentKind] = mapped_column(enum_column(PaymentKind))
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(String(255))
    received_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    reservation = relationship("Reservation", back_populates="payments")
