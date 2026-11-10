from datetime import datetime, time, timedelta
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import case, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, StaffUser
from app.core.config import settings
from app.core.security import utcnow
from app.models import Car, MaintenanceRecord, Payment, Rental, Reservation
from app.models.enums import CarStatus, MaintenanceStatus, PaymentKind, RentalStatus, ReservationStatus
from app.schemas.booking import ReservationOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _signed_amount():
    return case((Payment.kind == PaymentKind.refund, -Payment.amount), else_=Payment.amount)


@router.get("")
def dashboard(db: DB, _: StaffUser):
    now = utcnow()
    day_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    day_end = day_start + timedelta(days=1)
    month_start = day_start.replace(day=1)

    cars_by_status = {s.value: 0 for s in CarStatus}
    for status_, count in db.execute(select(Car.status, func.count()).group_by(Car.status)):
        cars_by_status[status_.value] = count
    fleet = sum(cars_by_status.values()) - cars_by_status["retired"]

    revenue_kinds = (PaymentKind.payment, PaymentKind.refund)
    revenue_month = db.scalar(
        select(func.coalesce(func.sum(_signed_amount()), 0)).where(
            Payment.kind.in_(revenue_kinds), Payment.created_at >= month_start
        )
    )

    # Revenue for the last 6 months
    six_months_ago = (month_start - timedelta(days=150)).replace(day=1)
    month_col = func.date_trunc("month", Payment.created_at)
    revenue_rows = db.execute(
        select(month_col, func.sum(_signed_amount()))
        .where(Payment.kind.in_(revenue_kinds), Payment.created_at >= six_months_ago)
        .group_by(month_col)
        .order_by(month_col)
    ).all()

    def count(stmt) -> int:
        return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    upcoming = db.scalars(
        select(Reservation)
        .where(Reservation.status == ReservationStatus.confirmed, Reservation.start_at >= day_start)
        .options(selectinload(Reservation.car), selectinload(Reservation.customer))
        .order_by(Reservation.start_at)
        .limit(8)
    ).all()
    overdue = db.scalars(
        select(Reservation)
        .where(Reservation.status == ReservationStatus.active, Reservation.end_at < now)
        .options(selectinload(Reservation.car), selectinload(Reservation.customer))
        .order_by(Reservation.end_at)
        .limit(8)
    ).all()

    return {
        "currency": settings.currency,
        "cars_by_status": cars_by_status,
        "fleet_size": fleet,
        "utilization_pct": round(100 * cars_by_status["rented"] / fleet, 1) if fleet else 0,
        "active_rentals": count(select(Rental.id).where(Rental.status == RentalStatus.open)),
        "overdue_rentals": count(
            select(Reservation.id).where(Reservation.status == ReservationStatus.active, Reservation.end_at < now)
        ),
        "pending_reservations": count(select(Reservation.id).where(Reservation.status == ReservationStatus.pending)),
        "pickups_today": count(
            select(Reservation.id).where(
                Reservation.status == ReservationStatus.confirmed,
                Reservation.start_at >= day_start,
                Reservation.start_at < day_end,
            )
        ),
        "returns_today": count(
            select(Reservation.id).where(
                Reservation.status == ReservationStatus.active,
                Reservation.end_at >= day_start,
                Reservation.end_at < day_end,
            )
        ),
        "open_maintenance": count(
            select(MaintenanceRecord.id).where(
                MaintenanceRecord.status.in_([MaintenanceStatus.scheduled, MaintenanceStatus.in_progress])
            )
        ),
        "revenue_month": str(Decimal(revenue_month or 0)),
        "revenue_by_month": [{"month": m.strftime("%Y-%m"), "amount": str(a)} for m, a in revenue_rows],
        "upcoming_pickups": [ReservationOut.model_validate(r).model_dump(mode="json") for r in upcoming],
        "overdue": [ReservationOut.model_validate(r).model_dump(mode="json") for r in overdue],
    }
