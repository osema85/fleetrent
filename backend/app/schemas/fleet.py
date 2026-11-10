import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import EmailStr, Field, field_validator

from app.models.enums import (
    CarCategory,
    CarStatus,
    FuelType,
    MaintenanceStatus,
    MaintenanceType,
    Transmission,
)
from app.schemas.common import InputModel, LongText, Mileage, Money, OutputModel, Phone, PositiveMoney

# ------------------------------------------------------------------ branches


class BranchBase(InputModel):
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    phone: Phone
    email: EmailStr | None = None


class BranchCreate(BranchBase):
    pass


class BranchUpdate(InputModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    phone: Phone | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


class BranchOut(OutputModel):
    id: uuid.UUID
    name: str
    address: str
    city: str
    phone: str
    email: str | None
    is_active: bool


# ------------------------------------------------------------------ cars

PLATE_PATTERN = r"^[A-Z0-9][A-Z0-9\- ]{1,19}$"
VIN_PATTERN = r"^[A-HJ-NPR-Z0-9]{17}$"  # 17 chars, no I/O/Q


def _upper(value: str | None) -> str | None:
    return value.upper() if isinstance(value, str) else value


class CarCreate(InputModel):
    branch_id: uuid.UUID | None = None
    make: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=60)
    year: int = Field(ge=1990, le=datetime.now().year + 1)
    plate_number: str = Field(pattern=PLATE_PATTERN)
    vin: str = Field(pattern=VIN_PATTERN)
    color: str = Field(min_length=1, max_length=30)
    category: CarCategory
    transmission: Transmission
    fuel_type: FuelType
    seats: int = Field(ge=1, le=20)
    mileage: Mileage = 0
    daily_rate: PositiveMoney
    notes: LongText | None = None

    @field_validator("plate_number", "vin", mode="before")
    @classmethod
    def normalize_ids(cls, value: str | None) -> str | None:
        return _upper(value)


class CarUpdate(InputModel):
    branch_id: uuid.UUID | None = None
    make: str | None = Field(default=None, min_length=1, max_length=60)
    model: str | None = Field(default=None, min_length=1, max_length=60)
    year: int | None = Field(default=None, ge=1990, le=datetime.now().year + 1)
    plate_number: str | None = Field(default=None, pattern=PLATE_PATTERN)
    vin: str | None = Field(default=None, pattern=VIN_PATTERN)
    color: str | None = Field(default=None, min_length=1, max_length=30)
    category: CarCategory | None = None
    transmission: Transmission | None = None
    fuel_type: FuelType | None = None
    seats: int | None = Field(default=None, ge=1, le=20)
    mileage: Mileage | None = None
    daily_rate: PositiveMoney | None = None
    status: CarStatus | None = None
    notes: LongText | None = None

    @field_validator("plate_number", "vin", mode="before")
    @classmethod
    def normalize_ids(cls, value: str | None) -> str | None:
        return _upper(value)


class CarPublic(OutputModel):
    """What customers may see."""

    id: uuid.UUID
    branch_id: uuid.UUID | None
    make: str
    model: str
    year: int
    color: str
    category: CarCategory
    transmission: Transmission
    fuel_type: FuelType
    seats: int
    daily_rate: Decimal


class CarOut(CarPublic):
    plate_number: str
    vin: str
    mileage: int
    status: CarStatus
    notes: str | None
    created_at: datetime


# ------------------------------------------------------------------ maintenance


class MaintenanceCreate(InputModel):
    car_id: uuid.UUID
    type: MaintenanceType
    description: str = Field(min_length=1, max_length=2000)
    scheduled_date: date
    cost: Money = Decimal("0")
    mileage: Mileage | None = None
    vendor: str | None = Field(default=None, max_length=120)


class MaintenanceUpdate(InputModel):
    status: MaintenanceStatus | None = None
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    scheduled_date: date | None = None
    cost: Money | None = None
    mileage: Mileage | None = None
    vendor: str | None = Field(default=None, max_length=120)


class CarBrief(OutputModel):
    id: uuid.UUID
    make: str
    model: str
    plate_number: str


class MaintenanceOut(OutputModel):
    id: uuid.UUID
    car_id: uuid.UUID
    car: CarBrief
    type: MaintenanceType
    status: MaintenanceStatus
    description: str
    scheduled_date: date
    completed_date: date | None
    cost: Decimal
    mileage: int | None
    vendor: str | None
    created_at: datetime
