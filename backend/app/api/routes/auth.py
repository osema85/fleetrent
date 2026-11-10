import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select, update

from app.api.deps import DB, CurrentUser, require_csrf
from app.core.config import settings
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    needs_rehash,
    utcnow,
    validate_password_strength,
    verify_password,
)
from app.models import Customer, RefreshToken, User
from app.models.enums import UserRole
from app.schemas.user import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import audit
from app.services.audit import client_ip

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "fr_refresh"
COOKIE_PATH = "/api/auth"
INVALID_LOGIN = "Invalid email or password, or the account is temporarily locked."
# A rotated token re-used within this window is treated as a benign race (two tabs), not theft
REUSE_GRACE = timedelta(seconds=10)


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,  # not readable by JavaScript -> safe from XSS token theft
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH, secure=settings.cookie_secure, samesite="strict")


def _issue_session(
    db: DB, request: Request, response: Response, user: User, family_id: uuid.UUID | None = None
) -> TokenResponse:
    raw = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            family_id=family_id or uuid.uuid4(),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
            ip=client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:255],
        )
    )
    access, expires_in = create_access_token(user.id, user.role.value)
    _set_refresh_cookie(response, raw)
    return TokenResponse(access_token=access, expires_in=expires_in, user=UserOut.model_validate(user))


def revoke_all_sessions(db: DB, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DB):
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    now = utcnow()

    if user is None:
        verify_password(payload.password, DUMMY_HASH)  # equalize response time
        audit.record(db, request, None, "login_failed", "user", details={"email": email, "reason": "unknown"})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)

    if user.locked_until and user.locked_until > now:
        audit.record(db, request, user, "login_blocked", "user", user.id, {"reason": "locked"})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        details = {"reason": "bad_password", "attempts": user.failed_login_attempts}
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
            details["locked"] = True
        audit.record(db, request, user, "login_failed", "user", user.id, details)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)

    if not user.is_active:
        audit.record(db, request, user, "login_blocked", "user", user.id, {"reason": "inactive"})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(payload.password)
    result = _issue_session(db, request, response, user)
    audit.record(db, request, user, "login", "user", user.id)
    db.commit()
    return result


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(require_csrf)])
def refresh(request: Request, response: Response, db: DB):
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No session")

    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)).with_for_update())
    now = utcnow()
    if token is None or token.expires_at <= now:
        _clear_refresh_cookie(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    if token.revoked_at is not None:
        if now - token.revoked_at > REUSE_GRACE:
            # A rotated token was replayed: likely stolen. Kill the whole session family.
            db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            audit.record(db, request, None, "refresh_token_reuse", "user", token.user_id)
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        token.revoked_at = now
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    token.revoked_at = now  # rotation: every refresh token is single-use
    result = _issue_session(db, request, response, user, family_id=token.family_id)
    db.commit()
    return result


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf)])
def logout(request: Request, response: Response, db: DB):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
        if token:
            db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=utcnow())
            )
            audit.record(db, request, None, "logout", "user", token.user_id)
            db.commit()
    _clear_refresh_cookie(response)
    response.status_code = 204
    return response


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, request: Request, db: DB):
    if not settings.allow_self_registration:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Online registration is disabled")
    email = str(payload.email).lower()
    exists = db.scalar(
        select(User.id).where(User.email == email).union(
            select(Customer.id).where(
                or_(Customer.email == email, Customer.driver_license_number == payload.driver_license_number)
            )
        )
    )
    if exists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An account with these details already exists. Contact the agency if you need access.",
        )

    user = User(
        email=email,
        full_name=f"{payload.first_name} {payload.last_name}",
        hashed_password=hash_password(payload.password),
        role=UserRole.customer,
    )
    db.add(user)
    db.flush()
    db.add(
        Customer(
            user_id=user.id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=email,
            phone=payload.phone,
            date_of_birth=payload.date_of_birth,
            driver_license_number=payload.driver_license_number.upper(),
            license_country=payload.license_country,
            license_expiry=payload.license_expiry,
        )
    )
    audit.record(db, request, user, "register", "user", user.id)
    db.commit()
    return user


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/change-password", status_code=204)
def change_password(payload: ChangePasswordRequest, request: Request, response: Response, user: CurrentUser, db: DB):
    if not verify_password(payload.current_password, user.hashed_password):
        audit.record(db, request, user, "password_change_failed", "user", user.id)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    try:
        validate_password_strength(payload.new_password, user.email)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "New password must differ from the current one")

    user.hashed_password = hash_password(payload.new_password)
    user.password_changed_at = utcnow()
    revoke_all_sessions(db, user.id)  # log out every device
    audit.record(db, request, user, "password_changed", "user", user.id)
    db.commit()
    _clear_refresh_cookie(response)
    response.status_code = 204
    return response
