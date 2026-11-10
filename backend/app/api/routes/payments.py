import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select

from app.api.deps import DB, CurrentUser, StaffUser
from app.api.routes.reservations import load_reservation
from app.models import Payment
from app.models.enums import PaymentKind, PaymentMethod
from app.schemas.booking import Balance, PaymentCreate, PaymentOut
from app.schemas.common import Page
from app.services import audit
from app.services.billing import balance_for

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=Page[PaymentOut])
def list_payments(
    db: DB,
    _: StaffUser,
    kind: PaymentKind | None = None,
    method: PaymentMethod | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Payment)
    if kind:
        stmt = stmt.where(Payment.kind == kind)
    if method:
        stmt = stmt.where(Payment.method == method)
    if from_date:
        stmt = stmt.where(Payment.created_at >= datetime.combine(from_date, datetime.min.time()).astimezone())
    if to_date:
        stmt = stmt.where(
            Payment.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()).astimezone()
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Payment.created_at.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": total or 0}


@router.get("/reservation/{reservation_id}", response_model=list[PaymentOut])
def reservation_payments(reservation_id: uuid.UUID, db: DB, user: CurrentUser):
    return load_reservation(db, reservation_id, user).payments


@router.get("/reservation/{reservation_id}/balance", response_model=Balance)
def reservation_balance(reservation_id: uuid.UUID, db: DB, user: CurrentUser):
    return balance_for(load_reservation(db, reservation_id, user))


@router.post("", response_model=PaymentOut, status_code=201)
def record_payment(payload: PaymentCreate, request: Request, db: DB, user: StaffUser):
    reservation = load_reservation(db, payload.reservation_id, user)
    bal = balance_for(reservation)
    if payload.kind == PaymentKind.refund and payload.amount > bal.paid:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Refund exceeds the amount paid")
    if payload.kind == PaymentKind.deposit_refund and payload.amount > bal.deposit_held:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Deposit refund exceeds the deposit held")

    payment = Payment(**payload.model_dump(), received_by_id=user.id)
    db.add(payment)
    db.flush()
    audit.record(
        db, request, user, f"payment_{payload.kind.value}", "payment", payment.id,
        {"code": reservation.code, "amount": str(payload.amount), "method": payload.method.value},
    )
    db.commit()
    return payment
