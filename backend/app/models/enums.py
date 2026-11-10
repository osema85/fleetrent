import enum

from sqlalchemy import Enum as SAEnum


class UserRole(enum.StrEnum):
    admin = "admin"
    manager = "manager"
    agent = "agent"
    customer = "customer"


STAFF_ROLES = (UserRole.admin, UserRole.manager, UserRole.agent)
MANAGER_ROLES = (UserRole.admin, UserRole.manager)


class CarStatus(enum.StrEnum):
    available = "available"
    rented = "rented"
    maintenance = "maintenance"
    retired = "retired"


class CarCategory(enum.StrEnum):
    economy = "economy"
    compact = "compact"
    midsize = "midsize"
    suv = "suv"
    luxury = "luxury"
    van = "van"


class Transmission(enum.StrEnum):
    manual = "manual"
    automatic = "automatic"


class FuelType(enum.StrEnum):
    petrol = "petrol"
    diesel = "diesel"
    hybrid = "hybrid"
    electric = "electric"


class ReservationStatus(enum.StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


# Reservations in these states block the car for their time window
BLOCKING_STATUSES = (ReservationStatus.pending, ReservationStatus.confirmed, ReservationStatus.active)


class InsuranceOption(enum.StrEnum):
    none = "none"
    basic = "basic"
    full = "full"


class RentalStatus(enum.StrEnum):
    open = "open"
    closed = "closed"


class PaymentMethod(enum.StrEnum):
    cash = "cash"
    card = "card"
    bank_transfer = "bank_transfer"


class PaymentKind(enum.StrEnum):
    payment = "payment"
    refund = "refund"
    deposit = "deposit"
    deposit_refund = "deposit_refund"


class MaintenanceType(enum.StrEnum):
    service = "service"
    repair = "repair"
    inspection = "inspection"
    tires = "tires"
    cleaning = "cleaning"
    other = "other"


class MaintenanceStatus(enum.StrEnum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


def enum_column(enum_cls: type[enum.Enum]) -> SAEnum:
    """Store enums as VARCHAR(20) — avoids painful native-enum migrations."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        validate_strings=True,
        values_callable=lambda members: [m.value for m in members],
    )
