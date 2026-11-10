import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    CarCategory,
    CarStatus,
    FuelType,
    MaintenanceStatus,
    MaintenanceType,
    Transmission,
    enum_column,
)


class Branch(TimestampMixin, Base):
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Car(TimestampMixin, Base):
    __tablename__ = "cars"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"), index=True)
    make: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(60))
    year: Mapped[int] = mapped_column(Integer)
    plate_number: Mapped[str] = mapped_column(String(20), unique=True)
    vin: Mapped[str] = mapped_column(String(17), unique=True)
    color: Mapped[str] = mapped_column(String(30))
    category: Mapped[CarCategory] = mapped_column(enum_column(CarCategory))
    transmission: Mapped[Transmission] = mapped_column(enum_column(Transmission))
    fuel_type: Mapped[FuelType] = mapped_column(enum_column(FuelType))
    seats: Mapped[int] = mapped_column(Integer)
    mileage: Mapped[int] = mapped_column(Integer, default=0)
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[CarStatus] = mapped_column(enum_column(CarStatus), default=CarStatus.available, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")


class MaintenanceRecord(TimestampMixin, Base):
    __tablename__ = "maintenance_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    car_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cars.id", ondelete="CASCADE"), index=True)
    type: Mapped[MaintenanceType] = mapped_column(enum_column(MaintenanceType))
    status: Mapped[MaintenanceStatus] = mapped_column(
        enum_column(MaintenanceStatus), default=MaintenanceStatus.scheduled
    )
    description: Mapped[str] = mapped_column(Text)
    scheduled_date: Mapped[date] = mapped_column(Date)
    completed_date: Mapped[date | None] = mapped_column(Date)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    mileage: Mapped[int | None] = mapped_column(Integer)
    vendor: Mapped[str | None] = mapped_column(String(120))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    car = relationship("Car")
