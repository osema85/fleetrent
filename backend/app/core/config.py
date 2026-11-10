"""Application settings, loaded from environment variables only (never from files in the repo)."""

from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

PLACEHOLDER = "CHANGE_ME"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # General
    environment: Literal["development", "production"] = "production"
    company_name: str = "FleetRent Car Rental"
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    tax_rate: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)

    # Database
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str = Field(min_length=12)

    # Auth
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "fleetrent-api"
    jwt_audience: str = "fleetrent-web"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=60)
    cookie_secure: bool = True
    max_failed_logins: int = Field(default=5, ge=1, le=50)
    lockout_minutes: int = Field(default=15, ge=1, le=1440)
    allow_self_registration: bool = True

    # HTTP
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = ""

    # Bootstrap
    first_admin_email: str = ""
    first_admin_password: str = ""
    seed_demo_data: bool = False

    # Business rules
    min_driver_age: int = 21
    max_rental_days: int = 90
    late_grace_minutes: int = 60
    late_day_multiplier: Decimal = Decimal("1.25")
    km_allowance_per_day: int = 300
    extra_km_fee: Decimal = Decimal("0.30")
    fuel_fee_per_percent: Decimal = Decimal("1.50")

    @field_validator("secret_key", "postgres_password")
    @classmethod
    def no_placeholders(cls, value: str) -> str:
        if PLACEHOLDER in value:
            raise ValueError("still contains the CHANGE_ME placeholder; run scripts/generate-env.sh")
        return value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def allowed_hosts_list(self) -> list[str]:
        hosts = [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]
        # The container health check calls the API on 127.0.0.1
        if "127.0.0.1" not in hosts:
            hosts.append("127.0.0.1")
        return hosts

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
