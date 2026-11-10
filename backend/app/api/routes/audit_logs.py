import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, AdminUser
from app.models import AuditLog
from app.schemas.common import OutputModel, Page

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditOut(OutputModel):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID | None
    user_email: str | None = None
    action: str
    entity_type: str | None
    entity_id: str | None
    details: dict
    ip: str | None


@router.get("", response_model=Page[AuditOut])
def list_audit_logs(
    db: DB,
    _: AdminUser,
    action: str | None = Query(default=None, max_length=60),
    user_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"%{action}%"))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.options(selectinload(AuditLog.user)).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    ).all()
    items = [
        AuditOut.model_validate(r).model_copy(update={"user_email": r.user.email if r.user else None}) for r in rows
    ]
    return {"items": items, "total": total or 0}
