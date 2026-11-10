import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, AdminUser, CurrentUser, is_staff
from app.models import Branch
from app.schemas.fleet import BranchCreate, BranchOut, BranchUpdate
from app.services import audit

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("", response_model=list[BranchOut])
def list_branches(db: DB, user: CurrentUser):
    stmt = select(Branch).order_by(Branch.name)
    if not is_staff(user):
        stmt = stmt.where(Branch.is_active.is_(True))
    return db.scalars(stmt).all()


@router.post("", response_model=BranchOut, status_code=201)
def create_branch(payload: BranchCreate, request: Request, db: DB, admin: AdminUser):
    branch = Branch(**payload.model_dump())
    db.add(branch)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A branch with this name already exists") from None
    audit.record(db, request, admin, "branch_created", "branch", branch.id, {"name": branch.name})
    db.commit()
    return branch


@router.patch("/{branch_id}", response_model=BranchOut)
def update_branch(branch_id: uuid.UUID, payload: BranchUpdate, request: Request, db: DB, admin: AdminUser):
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(branch, key, value)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A branch with this name already exists") from None
    audit.record(db, request, admin, "branch_updated", "branch", branch.id, {k: str(v) for k, v in changes.items()})
    db.commit()
    return branch
