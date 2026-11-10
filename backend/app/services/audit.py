from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def client_ip(request: Request | None) -> str | None:
    # uvicorn --proxy-headers sets request.client from the X-Forwarded-For header that nginx
    # overwrites with the real peer address, so clients cannot spoof it.
    if request is None or request.client is None:
        return None
    return request.client.host[:45]


def record(
    db: Session,
    request: Request | None,
    actor: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: Any = None,
    details: dict | None = None,
) -> None:
    """Add an audit entry to the current transaction (committed together with the change)."""
    db.add(
        AuditLog(
            user_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
            ip=client_ip(request),
        )
    )
