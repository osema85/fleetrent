"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _enum() -> sa.String:
    return sa.String(20)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", _enum(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("branches.id", ondelete="SET NULL")),
        *_timestamps(),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("ip", sa.String(45)),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    op.create_table(
        "cars",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("branches.id", ondelete="SET NULL")),
        sa.Column("make", sa.String(60), nullable=False),
        sa.Column("model", sa.String(60), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("plate_number", sa.String(20), nullable=False, unique=True),
        sa.Column("vin", sa.String(17), nullable=False, unique=True),
        sa.Column("color", sa.String(30), nullable=False),
        sa.Column("category", _enum(), nullable=False),
        sa.Column("transmission", _enum(), nullable=False),
        sa.Column("fuel_type", _enum(), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("mileage", sa.Integer(), nullable=False),
        sa.Column("daily_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("notes", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_cars_branch_id", "cars", ["branch_id"])
    op.create_index("ix_cars_status", "cars", ["status"])

    op.create_table(
        "maintenance_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("car_id", sa.Uuid(), sa.ForeignKey("cars.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", _enum(), nullable=False),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("completed_date", sa.Date()),
        sa.Column("cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("mileage", sa.Integer()),
        sa.Column("vendor", sa.String(120)),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_timestamps(),
    )
    op.create_index("ix_maintenance_records_car_id", "maintenance_records", ["car_id"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("address", sa.String(255)),
        sa.Column("city", sa.String(100)),
        sa.Column("country", sa.String(100)),
        sa.Column("driver_license_number", sa.String(50), nullable=False, unique=True),
        sa.Column("license_country", sa.String(100), nullable=False),
        sa.Column("license_expiry", sa.Date(), nullable=False),
        sa.Column("id_document_number", sa.String(50)),
        sa.Column("is_blacklisted", sa.Boolean(), nullable=False),
        sa.Column("blacklist_reason", sa.String(255)),
        sa.Column("notes", sa.Text()),
        *_timestamps(),
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(12), nullable=False, unique=True),
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("car_id", sa.Uuid(), sa.ForeignKey("cars.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("pickup_branch_id", sa.Uuid(), sa.ForeignKey("branches.id", ondelete="SET NULL")),
        sa.Column("return_branch_id", sa.Uuid(), sa.ForeignKey("branches.id", ondelete="SET NULL")),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("daily_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("insurance", _enum(), nullable=False),
        sa.Column("gps", sa.Boolean(), nullable=False),
        sa.Column("child_seat", sa.Boolean(), nullable=False),
        sa.Column("additional_driver", sa.Boolean(), nullable=False),
        sa.Column("estimated_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("cancel_reason", sa.String(255)),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.CheckConstraint("end_at > start_at", name="ck_reservations_period"),
    )
    op.create_index("ix_reservations_customer_id", "reservations", ["customer_id"])
    op.create_index("ix_reservations_car_id", "reservations", ["car_id"])
    op.create_index("ix_reservations_start_at", "reservations", ["start_at"])
    op.create_index("ix_reservations_status", "reservations", ["status"])
    # The last line of defense against double bookings, even under concurrent requests
    op.execute(
        """
        ALTER TABLE reservations ADD CONSTRAINT ex_reservations_no_overlap
        EXCLUDE USING gist (car_id WITH =, tstzrange(start_at, end_at, '[)') WITH &&)
        WHERE (status IN ('pending', 'confirmed', 'active'))
        """
    )

    op.create_table(
        "rentals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "reservation_id", sa.Uuid(), sa.ForeignKey("reservations.id", ondelete="RESTRICT"),
            nullable=False, unique=True,
        ),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_out_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("start_mileage", sa.Integer(), nullable=False),
        sa.Column("start_fuel_level", sa.Integer(), nullable=False),
        sa.Column("checkout_notes", sa.Text()),
        sa.Column("checked_in_at", sa.DateTime(timezone=True)),
        sa.Column("checked_in_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("end_mileage", sa.Integer()),
        sa.Column("end_fuel_level", sa.Integer()),
        sa.Column("damage_notes", sa.Text()),
        *[
            sa.Column(name, sa.Numeric(10, 2))
            for name in (
                "base_amount", "extras_amount", "late_fee", "mileage_fee",
                "fuel_fee", "damage_fee", "tax_amount", "total_amount",
            )
        ],
        *_timestamps(),
    )
    op.create_index("ix_rentals_status", "rentals", ["status"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reservation_id", sa.Uuid(), sa.ForeignKey("reservations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("method", _enum(), nullable=False),
        sa.Column("kind", _enum(), nullable=False),
        sa.Column("reference", sa.String(100)),
        sa.Column("notes", sa.String(255)),
        sa.Column("received_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )
    op.create_index("ix_payments_reservation_id", "payments", ["reservation_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(60)),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("ip", sa.String(45)),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    for table in (
        "audit_logs", "payments", "rentals", "reservations", "customers",
        "maintenance_records", "cars", "refresh_tokens", "users", "branches",
    ):
        op.drop_table(table)
