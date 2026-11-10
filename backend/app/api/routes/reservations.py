import secrets
import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, StaffUser, is_staff
from app.api.routes.cars import car_is_free, get_car_or_404
from app.core.config import settings
from app.core.security import utcnow
from app.models import Branch, Customer, Reservation, User
from app.models.enums import CarStatus, ReservationStatus
from app.schemas.booking import (
    CancelRequest,
    InvoiceOut,
    LineItem,
    PaymentOut,
    QuoteOut,
    QuoteRequest,
    ReservationCreate,
    RentalOut,
    ReservationOut,
)
from app.schemas.common import Page
from app.services import audit, pricing
from app.services.billing import balance_for

router = APIRouter(prefix="/reservations", tags=["reservations"])

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous 0/O/1/I


def _new_code() -> str:
    return "R-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def _age_on(birth: date, day: date) -> int:
    return day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day))


def _customer_for(db: DB, user: User) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.user_id == user.id))


def load_reservation(db: DB, reservation_id: uuid.UUID, user: User) -> Reservation:
    """Fetch a reservation and enforce ownership (customers only see their own -> no IDOR)."""
    reservation = db.scalar(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(
            selectinload(Reservation.car),
            selectinload(Reservation.customer),
            selectinload(Reservation.rental),
            selectinload(Reservation.payments),
        )
    )
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")
    if not is_staff(user):
        customer = _customer_for(db, user)
        if customer is None or reservation.customer_id != customer.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")
    return reservation


@router.post("/quote", response_model=QuoteOut)
def get_quote(payload: QuoteRequest, db: DB, _: CurrentUser):
    car = get_car_or_404(db, payload.car_id)
    q = pricing.quote(
        car.daily_rate, payload.start_at, payload.end_at,
        payload.insurance, payload.gps, payload.child_seat, payload.additional_driver,
    )
    return QuoteOut(
        **q.__dict__, deposit=pricing.deposit_for(car.category, payload.insurance), currency=settings.currency
    )


@router.get("", response_model=Page[ReservationOut])
def list_reservations(
    db: DB,
    user: CurrentUser,
    status_: ReservationStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=100),
    customer_id: uuid.UUID | None = None,
    car_id: uuid.UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Reservation).join(Reservation.customer)
    if not is_staff(user):
        customer = _customer_for(db, user)
        if customer is None:
            return {"items": [], "total": 0}
        stmt = stmt.where(Reservation.customer_id == customer.id)
    elif customer_id:
        stmt = stmt.where(Reservation.customer_id == customer_id)
    if car_id:
        stmt = stmt.where(Reservation.car_id == car_id)
    if status_:
        stmt = stmt.where(Reservation.status == status_)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Reservation.code).like(like),
                func.lower(Customer.last_name).like(like),
                func.lower(Customer.email).like(like),
            )
        )
    if from_date:
        stmt = stmt.where(Reservation.end_at >= datetime.combine(from_date, datetime.min.time()).astimezone())
    if to_date:
        stmt = stmt.where(
            Reservation.start_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()).astimezone()
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(
        stmt.options(selectinload(Reservation.car), selectinload(Reservation.customer))
        .order_by(Reservation.start_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": items, "total": total or 0}


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(payload: ReservationCreate, request: Request, db: DB, user: CurrentUser):
    # --- who is the customer?
    if is_staff(user):
        if payload.customer_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "customer_id is required")
        customer = db.get(Customer, payload.customer_id)
        if customer is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    else:
        customer = _customer_for(db, user)
        if customer is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Complete your customer profile first")

    # --- business rules
    now = utcnow()
    if payload.start_at < now - timedelta(minutes=15):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Start time is in the past")
    if payload.end_at - payload.start_at > timedelta(days=settings.max_rental_days):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Maximum rental length is {settings.max_rental_days} days"
        )
    if customer.is_blacklisted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This customer cannot make reservations. Contact the agency.")
    if _age_on(customer.date_of_birth, payload.start_at.date()) < settings.min_driver_age:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Driver must be at least {settings.min_driver_age} years old"
        )
    if customer.license_expiry < payload.end_at.date():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Driver license expires before the return date")
    for branch_id in (payload.pickup_branch_id, payload.return_branch_id):
        if branch_id:
            branch = db.get(Branch, branch_id)
            if branch is None or not branch.is_active:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Branch not available")

    car = get_car_or_404(db, payload.car_id)
    if car.status in (CarStatus.maintenance, CarStatus.retired):
        raise HTTPException(status.HTTP_409_CONFLICT, "This car is not available for booking")
    if not car_is_free(db, car.id, payload.start_at, payload.end_at):
        raise HTTPException(status.HTTP_409_CONFLICT, "The car is already booked for these dates")

    q = pricing.quote(
        car.daily_rate, payload.start_at, payload.end_at,
        payload.insurance, payload.gps, payload.child_seat, payload.additional_driver,
    )
    reservation = Reservation(
        code=_new_code(),
        customer_id=customer.id,
        car_id=car.id,
        pickup_branch_id=payload.pickup_branch_id or car.branch_id,
        return_branch_id=payload.return_branch_id or payload.pickup_branch_id or car.branch_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        # Staff bookings are confirmed immediately; online bookings wait for staff approval
        status=ReservationStatus.confirmed if is_staff(user) else ReservationStatus.pending,
        daily_rate=car.daily_rate,
        insurance=payload.insurance,
        gps=payload.gps,
        child_seat=payload.child_seat,
        additional_driver=payload.additional_driver,
        estimated_total=q.total,
        deposit_amount=pricing.deposit_for(car.category, payload.insurance),
        notes=payload.notes,
        created_by_id=user.id,
    )
    db.add(reservation)
    try:
        db.flush()
    except IntegrityError:
        # The database exclusion constraint caught a concurrent double booking
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "The car is already booked for these dates") from None
    audit.record(db, request, user, "reservation_created", "reservation", reservation.id, {"code": reservation.code})
    db.commit()
    return load_reservation(db, reservation.id, user)


@router.get("/{reservation_id}", response_model=ReservationOut)
def get_reservation(reservation_id: uuid.UUID, db: DB, user: CurrentUser):
    return load_reservation(db, reservation_id, user)


def _transition(db: DB, request: Request, user: User, reservation: Reservation, new: ReservationStatus, **extra):
    reservation.status = new
    for key, value in extra.items():
        setattr(reservation, key, value)
    audit.record(
        db, request, user, f"reservation_{new.value}", "reservation", reservation.id, {"code": reservation.code}
    )
    db.commit()
    return load_reservation(db, reservation.id, user)


@router.post("/{reservation_id}/confirm", response_model=ReservationOut)
def confirm(reservation_id: uuid.UUID, request: Request, db: DB, user: StaffUser):
    reservation = load_reservation(db, reservation_id, user)
    if reservation.status != ReservationStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only pending reservations can be confirmed")
    return _transition(db, request, user, reservation, ReservationStatus.confirmed)


@router.post("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel(reservation_id: uuid.UUID, payload: CancelRequest, request: Request, db: DB, user: CurrentUser):
    reservation = load_reservation(db, reservation_id, user)
    if reservation.status not in (ReservationStatus.pending, ReservationStatus.confirmed):
        raise HTTPException(status.HTTP_409_CONFLICT, "This reservation can no longer be cancelled")
    if not is_staff(user) and reservation.start_at <= utcnow():
        raise HTTPException(status.HTTP_409_CONFLICT, "The rental has started; please contact the agency")
    return _transition(
        db, request, user, reservation, ReservationStatus.cancelled,
        cancel_reason=payload.reason or ("Cancelled by customer" if not is_staff(user) else "Cancelled by staff"),
    )


@router.post("/{reservation_id}/no-show", response_model=ReservationOut)
def no_show(reservation_id: uuid.UUID, request: Request, db: DB, user: StaffUser):
    reservation = load_reservation(db, reservation_id, user)
    if reservation.status != ReservationStatus.confirmed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only confirmed reservations can be marked as no-show")
    if reservation.start_at > utcnow():
        raise HTTPException(status.HTTP_409_CONFLICT, "The pickup time has not passed yet")
    return _transition(db, request, user, reservation, ReservationStatus.no_show)


@router.get("/{reservation_id}/invoice", response_model=InvoiceOut)
def invoice(reservation_id: uuid.UUID, db: DB, user: CurrentUser):
    r = load_reservation(db, reservation_id, user)
    rental = r.rental
    days = pricing.rental_days(r.start_at, r.end_at)
    if rental is not None and rental.total_amount is not None:
        items = [
            LineItem(label=f"Car rental — {days} day(s) × {r.daily_rate}", amount=rental.base_amount),
            LineItem(label="Insurance & extras", amount=rental.extras_amount),
            LineItem(label="Late return fee", amount=rental.late_fee),
            LineItem(label="Extra mileage", amount=rental.mileage_fee),
            LineItem(label="Fuel / charge refill", amount=rental.fuel_fee),
            LineItem(label="Damage", amount=rental.damage_fee),
        ]
        tax, total = rental.tax_amount, rental.total_amount
    else:
        q = pricing.quote(r.daily_rate, r.start_at, r.end_at, r.insurance, r.gps, r.child_seat, r.additional_driver)
        items = [
            LineItem(label=f"Car rental — {days} day(s) × {r.daily_rate}", amount=q.base_amount),
            LineItem(label="Insurance & extras", amount=q.extras_amount),
        ]
        tax, total = q.tax_amount, q.total
    items = [i for i in items if i.amount]
    return InvoiceOut(
        company_name=settings.company_name,
        currency=settings.currency,
        invoice_number=f"INV-{r.code[2:]}",
        issued_at=rental.checked_in_at if rental and rental.checked_in_at else utcnow(),
        reservation=ReservationOut.model_validate(r),
        rental=RentalOut.model_validate(rental) if rental else None,
        line_items=items,
        subtotal=sum((i.amount for i in items), start=pricing.money(0)),
        tax_rate=settings.tax_rate,
        tax_amount=tax,
        total=total,
        payments=[PaymentOut.model_validate(p) for p in r.payments],
        balance=balance_for(r),
    )
