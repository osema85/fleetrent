import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select

from app.api.deps import DB, AdminUser
from app.api.routes.auth import revoke_all_sessions
from app.core.security import hash_password, utcnow
from app.models import Branch, User
from app.models.enums import UserRole
from app.schemas.common import Page
from app.schemas.user import PasswordReset, UserCreate, UserOut, UserUpdate
from app.services import audit

router = APIRouter(prefix="/users", tags=["users"])


def _get(db: DB, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.get("", response_model=Page[UserOut])
def list_users(
    db: DB,
    _: AdminUser,
    q: str | None = Query(default=None, max_length=100),
    role: UserRole | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(User)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(User.email).like(like), func.lower(User.full_name).like(like)))
    if role:
        stmt = stmt.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": total or 0}


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, request: Request, db: DB, admin: AdminUser):
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
    if payload.branch_id and not db.get(Branch, payload.branch_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Branch not found")
    user = User(
        email=email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=hash_password(payload.password),
        branch_id=payload.branch_id,
    )
    db.add(user)
    db.flush()
    audit.record(db, request, admin, "user_created", "user", user.id, {"role": user.role.value})
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, payload: UserUpdate, request: Request, db: DB, admin: AdminUser):
    user = _get(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if user.id == admin.id and (
        changes.get("is_active") is False or ("role" in changes and changes["role"] != UserRole.admin)
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate or demote your own account")
    if changes.get("branch_id") and not db.get(Branch, changes["branch_id"]):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Branch not found")
    for key, value in changes.items():
        setattr(user, key, value)
    if changes.get("is_active") is False or "role" in changes:
        # Role/active changes take effect immediately: force re-login everywhere
        user.password_changed_at = utcnow()
        revoke_all_sessions(db, user.id)
    audit.record(db, request, admin, "user_updated", "user", user.id, {k: str(v) for k, v in changes.items()})
    db.commit()
    return user


@router.post("/{user_id}/reset-password", status_code=204)
def reset_password(user_id: uuid.UUID, payload: PasswordReset, request: Request, db: DB, admin: AdminUser):
    user = _get(db, user_id)
    user.hashed_password = hash_password(payload.new_password)
    user.password_changed_at = utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None
    revoke_all_sessions(db, user.id)
    audit.record(db, request, admin, "password_reset", "user", user.id)
    db.commit()


@router.post("/{user_id}/unlock", response_model=UserOut)
def unlock_user(user_id: uuid.UUID, request: Request, db: DB, admin: AdminUser):
    user = _get(db, user_id)
    user.failed_login_attempts = 0
    user.locked_until = None
    audit.record(db, request, admin, "user_unlocked", "user", user.id)
    db.commit()
    return user
