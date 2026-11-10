import uuid
from datetime import date, datetime

from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.security import validate_password_strength
from app.models.enums import UserRole
from app.schemas.common import InputModel, Name, OutputModel, Phone


class UserOut(OutputModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    branch_id: uuid.UUID | None
    last_login_at: datetime | None
    locked_until: datetime | None
    created_at: datetime


class TokenResponse(OutputModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class LoginRequest(InputModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(InputModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class RegisterRequest(InputModel):
    email: EmailStr
    password: str = Field(max_length=128)
    first_name: Name
    last_name: Name
    phone: Phone
    date_of_birth: date
    driver_license_number: str = Field(min_length=4, max_length=50, pattern=r"^[A-Za-z0-9\- ]+$")
    license_country: Name
    license_expiry: date

    @model_validator(mode="after")
    def check_password(self) -> "RegisterRequest":
        validate_password_strength(self.password, str(self.email))
        return self


class UserCreate(InputModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    role: UserRole
    password: str = Field(max_length=128)
    branch_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def check_password(self) -> "UserCreate":
        validate_password_strength(self.password, str(self.email))
        return self


class UserUpdate(InputModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    role: UserRole | None = None
    is_active: bool | None = None
    branch_id: uuid.UUID | None = None


class PasswordReset(InputModel):
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong(cls, value: str) -> str:
        return validate_password_strength(value)
