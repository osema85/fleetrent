import uuid
from datetime import date, datetime

from pydantic import EmailStr, Field

from app.schemas.common import InputModel, LongText, Name, OutputModel, Phone

LICENSE = r"^[A-Za-z0-9\- ]+$"


class CustomerCreate(InputModel):
    first_name: Name
    last_name: Name
    email: EmailStr
    phone: Phone
    date_of_birth: date
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    driver_license_number: str = Field(min_length=4, max_length=50, pattern=LICENSE)
    license_country: Name
    license_expiry: date
    id_document_number: str | None = Field(default=None, max_length=50)
    notes: LongText | None = None


class CustomerUpdate(InputModel):
    first_name: Name | None = None
    last_name: Name | None = None
    email: EmailStr | None = None
    phone: Phone | None = None
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    driver_license_number: str | None = Field(default=None, min_length=4, max_length=50, pattern=LICENSE)
    license_country: Name | None = None
    license_expiry: date | None = None
    id_document_number: str | None = Field(default=None, max_length=50)
    notes: LongText | None = None
    is_blacklisted: bool | None = None
    blacklist_reason: str | None = Field(default=None, max_length=255)


class CustomerSelfUpdate(InputModel):
    """Fields a customer may change on their own profile."""

    phone: Phone | None = None
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    driver_license_number: str | None = Field(default=None, min_length=4, max_length=50, pattern=LICENSE)
    license_country: Name | None = None
    license_expiry: date | None = None


class CustomerBrief(OutputModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str


class CustomerOut(CustomerBrief):
    user_id: uuid.UUID | None
    date_of_birth: date
    address: str | None
    city: str | None
    country: str | None
    driver_license_number: str
    license_country: str
    license_expiry: date
    id_document_number: str | None
    is_blacklisted: bool
    blacklist_reason: str | None
    notes: str | None
    created_at: datetime
