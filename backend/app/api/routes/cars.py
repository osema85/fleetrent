import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import AwareDatetime
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, AdminUser, CurrentUser, ManagerUser, StaffUser
from app.models import Branch, Car, Reservation
from app.models.enums import BLOCKING_STATUSES, CarCategory, CarStatus
from app.schemas.common import Page
from app.schemas.fleet import CarCreate, CarOut, CarPublic, CarUpdate
from app.services import audit

router = APIRouter(prefix="/cars", tags=["cars"])


def get_car_or_404(db: DB, car_id: uuid.UUID) -> Car:
    car = db.get(Car, car_id)
    if car is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Car not found")
    return car


def car_is_free(db: DB, car_id: uuid.UUID, start: datetime, end: datetime) -> bool:
    conflict = db.scalar(
        select(Reservation.id).where(
            Reservation.car_id == car_id,
            Reservation.status.in_(BLOCKING_STATUSES),
            Reservation.start_at < end,
            Reservation.end_at > start,
        )
    )
    return conflict is None


@router.get("", response_model=Page[CarOut])
def list_cars(
    db: DB,
    _: StaffUser,
    q: str | None = Query(default=None, max_length=100),
    status_: CarStatus | None = Query(default=None, alias="status"),
    category: CarCategory | None = None,
    branch_id: uuid.UUID | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Car)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Car.make).like(like),
                func.lower(Car.model).like(like),
                func.lower(Car.plate_number).like(like),
            )
        )
    if status_:
        stmt = stmt.where(Car.status == status_)
    if category:
        stmt = stmt.where(Car.category == category)
    if branch_id:
        stmt = stmt.where(Car.branch_id == branch_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Car.make, Car.model).limit(limit).offset(offset)).all()
    return {"items": items, "total": total or 0}


@router.get("/available", response_model=list[CarPublic])
def available_cars(
    db: DB,
    _: CurrentUser,
    start_at: AwareDatetime,
    end_at: AwareDatetime,
    category: CarCategory | None = None,
    branch_id: uuid.UUID | None = None,
):
    """Cars with no overlapping pending/confirmed/active reservation."""
    if end_at <= start_at:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "end_at must be after start_at")
    busy = select(Reservation.car_id).where(
        Reservation.status.in_(BLOCKING_STATUSES),
        Reservation.start_at < end_at,
        Reservation.end_at > start_at,
    )
    stmt = select(Car).where(
        Car.status.in_([CarStatus.available, CarStatus.rented]),
        Car.id.not_in(busy),
    )
    if category:
        stmt = stmt.where(Car.category == category)
    if branch_id:
        stmt = stmt.where(Car.branch_id == branch_id)
    return db.scalars(stmt.order_by(Car.daily_rate).limit(100)).all()


@router.get("/{car_id}", response_model=CarOut)
def get_car(car_id: uuid.UUID, db: DB, _: StaffUser):
    return get_car_or_404(db, car_id)


def _check_branch(db: DB, branch_id: uuid.UUID | None) -> None:
    if branch_id and not db.get(Branch, branch_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Branch not found")


@router.post("", response_model=CarOut, status_code=201)
def create_car(payload: CarCreate, request: Request, db: DB, user: ManagerUser):
    _check_branch(db, payload.branch_id)
    car = Car(**payload.model_dump())
    db.add(car)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Plate number or VIN already registered") from None
    audit.record(db, request, user, "car_created", "car", car.id, {"plate": car.plate_number})
    db.commit()
    return car


@router.patch("/{car_id}", response_model=CarOut)
def update_car(car_id: uuid.UUID, payload: CarUpdate, request: Request, db: DB, user: ManagerUser):
    car = get_car_or_404(db, car_id)
    changes = payload.model_dump(exclude_unset=True)
    if "branch_id" in changes:
        _check_branch(db, changes["branch_id"])
    new_status = changes.get("status")
    if new_status and new_status != car.status:
        if car.status == CarStatus.rented:
            raise HTTPException(status.HTTP_409_CONFLICT, "Car is currently rented; check it in first")
        if new_status == CarStatus.rented:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Use the check-out process to rent a car")
    if "mileage" in changes and changes["mileage"] < car.mileage:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Mileage cannot decrease")
    for key, value in changes.items():
        setattr(car, key, value)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Plate number or VIN already registered") from None
    audit.record(db, request, user, "car_updated", "car", car.id, {k: str(v) for k, v in changes.items()})
    db.commit()
    return car


@router.delete("/{car_id}", status_code=204)
def delete_car(car_id: uuid.UUID, request: Request, db: DB, admin: AdminUser):
    car = get_car_or_404(db, car_id)
    if db.scalar(select(Reservation.id).where(Reservation.car_id == car.id).limit(1)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Car has reservation history; set its status to 'retired' instead"
        )
    audit.record(db, request, admin, "car_deleted", "car", car.id, {"plate": car.plate_number})
    db.delete(car)
    db.commit()

