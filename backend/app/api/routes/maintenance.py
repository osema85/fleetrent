import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, ManagerUser, StaffUser
from app.api.routes.cars import get_car_or_404
from app.models import Car, MaintenanceRecord
from app.models.enums import CarStatus, MaintenanceStatus
from app.schemas.common import Page
from app.schemas.fleet import MaintenanceCreate, MaintenanceOut, MaintenanceUpdate
from app.services import audit

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

ALLOWED = {
    MaintenanceStatus.scheduled: {MaintenanceStatus.in_progress, MaintenanceStatus.completed, MaintenanceStatus.cancelled},
    MaintenanceStatus.in_progress: {MaintenanceStatus.completed, MaintenanceStatus.cancelled},
    MaintenanceStatus.completed: set(),
    MaintenanceStatus.cancelled: set(),
}


def _load(db: DB, record_id: uuid.UUID) -> MaintenanceRecord:
    record = db.scalar(
        select(MaintenanceRecord).where(MaintenanceRecord.id == record_id).options(selectinload(MaintenanceRecord.car))
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maintenance record not found")
    return record


@router.get("", response_model=Page[MaintenanceOut])
def list_maintenance(
    db: DB,
    _: StaffUser,
    car_id: uuid.UUID | None = None,
    status_: MaintenanceStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(MaintenanceRecord)
    if car_id:
        stmt = stmt.where(MaintenanceRecord.car_id == car_id)
    if status_:
        stmt = stmt.where(MaintenanceRecord.status == status_)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(
        stmt.options(selectinload(MaintenanceRecord.car))
        .order_by(MaintenanceRecord.scheduled_date.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": items, "total": total or 0}


@router.post("", response_model=MaintenanceOut, status_code=201)
def create_maintenance(payload: MaintenanceCreate, request: Request, db: DB, user: ManagerUser):
    car = get_car_or_404(db, payload.car_id)
    if car.status == CarStatus.retired:
        raise HTTPException(status.HTTP_409_CONFLICT, "Car is retired")
    record = MaintenanceRecord(**payload.model_dump(), created_by_id=user.id)
    db.add(record)
    db.flush()
    audit.record(db, request, user, "maintenance_created", "maintenance", record.id, {"car": car.plate_number})
    db.commit()
    return _load(db, record.id)


@router.patch("/{record_id}", response_model=MaintenanceOut)
def update_maintenance(record_id: uuid.UUID, payload: MaintenanceUpdate, request: Request, db: DB, user: ManagerUser):
    record = _load(db, record_id)
    changes = payload.model_dump(exclude_unset=True)
    new_status = changes.pop("status", None)
    for key, value in changes.items():
        setattr(record, key, value)

    if new_status and new_status != record.status:
        if new_status not in ALLOWED[record.status]:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"Cannot change from {record.status.value} to {new_status.value}"
            )
        car = db.scalar(select(Car).where(Car.id == record.car_id).with_for_update())
        if new_status == MaintenanceStatus.in_progress:
            if car.status == CarStatus.rented:
                raise HTTPException(status.HTTP_409_CONFLICT, "Car is currently rented")
            car.status = CarStatus.maintenance
        elif new_status in (MaintenanceStatus.completed, MaintenanceStatus.cancelled):
            if new_status == MaintenanceStatus.completed:
                record.completed_date = date.today()
                if record.mileage and record.mileage > car.mileage:
                    car.mileage = record.mileage
            if car.status == CarStatus.maintenance:
                car.status = CarStatus.available
        record.status = new_status
        changes["status"] = new_status

    audit.record(db, request, user, "maintenance_updated", "maintenance", record.id, {k: str(v) for k, v in changes.items()})
    db.commit()
    return _load(db, record.id)
