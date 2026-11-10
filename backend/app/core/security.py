"""Password hashing (Argon2id), password policy and token helpers."""

import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()  # Argon2id with OWASP-recommended defaults

# Used to spend the same time verifying when a user does not exist (prevents user enumeration by timing)
DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


def utcnow() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


def validate_password_strength(password: str, email: str | None = None) -> str:
    """Raise ValueError if the password does not meet the policy."""
    problems = []
    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        problems.append(f"at most {PASSWORD_MAX_LENGTH} characters")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"[A-Z]", password):
        problems.append("an uppercase letter")
    if not re.search(r"\d", password):
        problems.append("a digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("a symbol")
    if problems:
        raise ValueError("Password must contain " + ", ".join(problems) + ".")
    if email:
        local = email.split("@")[0].lower()
        if len(local) >= 4 and local in password.lower():
            raise ValueError("Password must not contain your email name.")
    return password


# ---------------------------------------------------------------- access tokens (JWT)


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    now = utcnow()
    expires = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": secrets.token_hex(16),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError if the token is invalid, expired or of the wrong type."""
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],  # pinned: prevents "alg" confusion attacks
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "sub", "type", "iss", "aud"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return payload


# ---------------------------------------------------------------- refresh tokens (opaque)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Refresh tokens are stored hashed, so a database leak does not leak sessions."""
    return hashlib.sha256(token.encode()).hexdigest()
