"""Authentication & authorization dependencies shared by all routes."""

import uuid
from typing import Annotated
from urllib.parse import urlparse

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.models.enums import MANAGER_ROLES, STAFF_ROLES, UserRole

DB = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)

CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "fleetrent"


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauthorized("Invalid or expired token") from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    # Tokens issued before the last password change are no longer valid
    if payload["iat"] < int(user.password_changed_at.timestamp()):
        raise _unauthorized("Session expired, please log in again")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission for this action")
        return user

    return checker


StaffUser = Annotated[User, Depends(require_roles(*STAFF_ROLES))]
ManagerUser = Annotated[User, Depends(require_roles(*MANAGER_ROLES))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.admin))]


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def require_csrf(request: Request) -> None:
    """Protects cookie-authenticated endpoints (refresh/logout) from cross-site requests.

    Browsers cannot send a custom header cross-origin without a CORS preflight, which we
    never approve, and the Origin header (when sent) must be one of our hosts.
    """
    if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing CSRF header")
    origin = request.headers.get("origin")
    if origin:
        host = urlparse(origin).hostname
        allowed = set(settings.allowed_hosts_list) | {urlparse(o).hostname for o in settings.cors_origins_list}
        if host not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Origin not allowed")
