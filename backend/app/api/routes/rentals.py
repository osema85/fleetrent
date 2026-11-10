import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, StaffUser
from app.api.routes.reservations import load_reservation
from app.core.security import utcnow
from app.models import Car, Rental, Reservation
from app.models.enums import CarStatus, RentalStatus, ReservationStatus
from app.schemas.booking import CheckinRequest, CheckoutRequest, RentalListItem, RentalOut
from app.schemas.common import Page
from app.services import audit, pricing

router = APIRouter(prefix="/rentals", tags=["rentals"])


@router.get("", response_model=Page[RentalListItem])
def list_rentals(
    db: DB,
    _: StaffUser,
    status_: RentalStatus | None = Query(default=None, alias="status"),
    overdue: bool = False,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Rental).join(Rental.reservation)
    if status_:
        stmt = stmt.where(Rental.status == status_)
    if overdue:
        stmt = stmt.where(Rental.status == RentalStatus.open, Reservation.end_at < utcnow())
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(
        stmt.options(
            selectinload(Rental.reservation).selectinload(Reservation.car),
            selectinload(Rental.reservation).selectinload(Reservation.customer),
        )
        .order_by(Rental.checked_out_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": items, "total": total or 0}


@router.post("/checkout", response_model=RentalOut, status_code=201)
def checkout(payload: CheckoutRequest, request: Request, db: DB, user: StaffUser):
    """Hand the keys to the customer: confirmed reservation -> active rental."""
    reservation = load_reservation(db, payload.reservation_id, user)
    if reservation.status != ReservationStatus.confirmed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only confirmed reservations can be checked out")
    now = utcnow()
    if now > reservation.end_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "The reservation period is already over")
    car = db.scalar(select(Car).where(Car.id == reservation.car_id).with_for_update().execution_options(populate_existing=True))
    if car.status != CarStatus.available:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Car is not available (status: {car.status.value})")
    if payload.start_mileage < car.mileage:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Mileage cannot be lower than the recorded {car.mileage} km"
        )

    rental = Rental(
        reservation_id=reservation.id,
        checked_out_at=now,
        checked_out_by_id=user.id,
        start_mileage=payload.start_mileage,
        start_fuel_level=payload.start_fuel_level,
        checkout_notes=payload.notes,
    )
    db.add(rental)
    car.status = CarStatus.rented
    car.mileage = payload.start_mileage
    reservation.status = ReservationStatus.active
    db.flush()
    audit.record(db, request, user, "rental_checkout", "rental", rental.id, {"code": reservation.code})
    db.commit()
    return rental


@router.post("/{rental_id}/checkin", response_model=RentalOut)
def checkin(rental_id: uuid.UUID, payload: CheckinRequest, request: Request, db: DB, user: StaffUser):
    """Vehicle returned: compute the final bill and free the car."""
    rental = db.scalar(select(Rental).where(Rental.id == rental_id).with_for_update())
    if rental is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rental not found")
    if rental.status != RentalStatus.open:
        raise HTTPException(status.HTTP_409_CONFLICT, "Rental is already closed")
    reservation = load_reservation(db, rental.reservation_id, user)

    now = utcnow()
    returned_at = payload.returned_at or now
    if returned_at > now or returned_at < rental.checked_out_at:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Return time must be between check-out and now")
    if payload.end_mileage < rental.start_mileage:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "End mileage is lower than start mileage")

    charges = pricing.final_charges(
        daily_rate=reservation.daily_rate,
        start_at=reservation.start_at,
        end_at=reservation.end_at,
        returned_at=returned_at,
        insurance=reservation.insurance,
        gps=reservation.gps,
        child_seat=reservation.child_seat,
        additional_driver=reservation.additional_driver,
        start_mileage=rental.start_mileage,
        end_mileage=payload.end_mileage,
        start_fuel=rental.start_fuel_level,
        end_fuel=payload.end_fuel_level,
        damage_fee=payload.damage_fee,
    )
    rental.status = RentalStatus.closed
    rental.checked_in_at = returned_at
    rental.checked_in_by_id = user.id
    rental.end_mileage = payload.end_mileage
    rental.end_fuel_level = payload.end_fuel_level
    rental.damage_notes = payload.damage_notes
    for key in (
        "base_amount", "extras_amount", "late_fee", "mileage_fee",
        "fuel_fee", "damage_fee", "tax_amount", "total_amount",
    ):
        setattr(rental, key, getattr(charges, key))

    car = db.scalar(select(Car).where(Car.id == reservation.car_id).with_for_update().execution_options(populate_existing=True))
    car.mileage = max(car.mileage, payload.end_mileage)
    car.status = CarStatus.maintenance if payload.send_to_maintenance else CarStatus.available
    if reservation.return_branch_id:
        car.branch_id = reservation.return_branch_id
    reservation.status = ReservationStatus.completed

    audit.record(
        db, request, user, "rental_checkin", "rental", rental.id,
        {"code": reservation.code, "total": str(charges.total_amount), "late_days": charges.late_days},
    )
    db.commit()
    return rental
