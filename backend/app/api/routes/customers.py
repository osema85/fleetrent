import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, AdminUser, CurrentUser, StaffUser
from app.models import Customer, Reservation
from app.models.enums import MANAGER_ROLES, UserRole
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerSelfUpdate, CustomerUpdate
from app.services import audit

router = APIRouter(prefix="/customers", tags=["customers"])

DUPLICATE = "A customer with this email or driver license already exists"


def _own_profile(db: DB, user) -> Customer:
    if user.role != UserRole.customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No customer profile for staff accounts")
    customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer profile not found")
    return customer


@router.get("/me", response_model=CustomerOut)
def my_profile(db: DB, user: CurrentUser):
    return _own_profile(db, user)


@router.patch("/me", response_model=CustomerOut)
def update_my_profile(payload: CustomerSelfUpdate, request: Request, db: DB, user: CurrentUser):
    customer = _own_profile(db, user)
    changes = payload.model_dump(exclude_unset=True)
    if "driver_license_number" in changes:
        changes["driver_license_number"] = changes["driver_license_number"].upper()
    for key, value in changes.items():
        setattr(customer, key, value)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE) from None
    audit.record(db, request, user, "customer_self_updated", "customer", customer.id, {"fields": list(changes)})
    db.commit()
    return customer


@router.get("", response_model=Page[CustomerOut])
def list_customers(
    db: DB,
    _: StaffUser,
    q: str | None = Query(default=None, max_length=100),
    blacklisted: bool | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Customer)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Customer.first_name).like(like),
                func.lower(Customer.last_name).like(like),
                func.lower(Customer.email).like(like),
                func.lower(Customer.phone).like(like),
                func.lower(Customer.driver_license_number).like(like),
            )
        )
    if blacklisted is not None:
        stmt = stmt.where(Customer.is_blacklisted.is_(blacklisted))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Customer.last_name, Customer.first_name).limit(limit).offset(offset)).all()
    return {"items": items, "total": total or 0}


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, request: Request, db: DB, user: StaffUser):
    data = payload.model_dump()
    data["email"] = data["email"].lower()
    data["driver_license_number"] = data["driver_license_number"].upper()
    customer = Customer(**data)
    db.add(customer)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE) from None
    audit.record(db, request, user, "customer_created", "customer", customer.id)
    db.commit()
    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: uuid.UUID, db: DB, _: StaffUser):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: uuid.UUID, payload: CustomerUpdate, request: Request, db: DB, user: StaffUser):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    changes = payload.model_dump(exclude_unset=True)
    if ("is_blacklisted" in changes or "blacklist_reason" in changes) and user.role not in MANAGER_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only managers can change the blacklist")
    if "email" in changes:
        changes["email"] = changes["email"].lower()
    if "driver_license_number" in changes:
        changes["driver_license_number"] = changes["driver_license_number"].upper()
    for key, value in changes.items():
        setattr(customer, key, value)
    if changes.get("is_blacklisted") is False:
        customer.blacklist_reason = None
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE) from None
    action = "customer_blacklisted" if changes.get("is_blacklisted") else "customer_updated"
    audit.record(db, request, user, action, "customer", customer.id, {"fields": list(changes)})
    db.commit()
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: uuid.UUID, request: Request, db: DB, admin: AdminUser):
    """Right to erasure: only possible when the customer has no rental history."""
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    if db.scalar(select(Reservation.id).where(Reservation.customer_id == customer.id).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Customer has reservation history and cannot be deleted")
    audit.record(db, request, admin, "customer_deleted", "customer", customer.id)
    db.delete(customer)
    db.commit()
