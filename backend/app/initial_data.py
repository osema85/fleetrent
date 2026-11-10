"""Run at container start: creates the first admin and (optionally) demo data. Idempotent."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password, validate_password_strength
from app.db.session import SessionLocal
from app.models import Branch, Car, Customer, User
from app.models.enums import CarCategory, FuelType, Transmission, UserRole

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fleetrent.init")


def ensure_admin(db) -> None:
    if db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.admin)):
        return
    email, password = settings.first_admin_email.strip().lower(), settings.first_admin_password
    if not email or not password:
        log.warning("No admin exists and FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD are not set.")
        return
    if "CHANGE_ME" in password:
        raise SystemExit("FIRST_ADMIN_PASSWORD still has the placeholder value. Run scripts/generate-env.sh")
    validate_password_strength(password, email)
    db.add(User(email=email, full_name="Administrator", role=UserRole.admin, hashed_password=hash_password(password)))
    log.info("Created first admin account %s", email)


def seed_demo(db) -> None:
    if db.scalar(select(func.count()).select_from(Branch)):
        return
    downtown = Branch(name="Downtown", address="12 Main Street", city="Springfield", phone="+1 555 0100",
                      email="downtown@fleetrent.example")
    airport = Branch(name="Airport", address="Terminal 2, Arrivals", city="Springfield", phone="+1 555 0200",
                     email="airport@fleetrent.example")
    db.add_all([downtown, airport])
    db.flush()

    cars = [
        ("Toyota", "Yaris", 2023, "AB-123-CD", "JTDBT923771234567", "White", CarCategory.economy, Transmission.manual, FuelType.petrol, 5, "35", downtown),
        ("Renault", "Clio", 2024, "EF-456-GH", "VF1RJA00012345678", "Red", CarCategory.economy, Transmission.manual, FuelType.petrol, 5, "38", airport),
        ("Volkswagen", "Golf", 2023, "IJ-789-KL", "WVWZZZAUZPW123456", "Grey", CarCategory.compact, Transmission.automatic, FuelType.diesel, 5, "49", downtown),
        ("Peugeot", "308", 2024, "MN-012-PQ", "VF3LBYHZPJS123456", "Blue", CarCategory.compact, Transmission.automatic, FuelType.hybrid, 5, "52", airport),
        ("Toyota", "Camry", 2023, "RS-345-TU", "4T1B11HK5JU123456", "Black", CarCategory.midsize, Transmission.automatic, FuelType.hybrid, 5, "65", downtown),
        ("Hyundai", "Tucson", 2024, "VW-678-XY", "KM8J33A46MU123456", "Silver", CarCategory.suv, Transmission.automatic, FuelType.hybrid, 5, "79", airport),
        ("Tesla", "Model Y", 2024, "ZA-901-BC", "7SAYGDEE5PF123456", "White", CarCategory.suv, Transmission.automatic, FuelType.electric, 5, "95", downtown),
        ("BMW", "5 Series", 2024, "DE-234-FG", "WBA53BJ0XPW123456", "Black", CarCategory.luxury, Transmission.automatic, FuelType.diesel, 5, "140", airport),
        ("Mercedes", "Vito", 2023, "HJ-567-KL", "WDF44770313123456", "White", CarCategory.van, Transmission.manual, FuelType.diesel, 9, "110", downtown),
    ]
    for make, model, year, plate, vin, color, cat, trans, fuel, seats, rate, branch in cars:
        db.add(Car(make=make, model=model, year=year, plate_number=plate, vin=vin, color=color, category=cat,
                   transmission=trans, fuel_type=fuel, seats=seats, daily_rate=Decimal(rate),
                   mileage=12000, branch_id=branch.id))

    db.add_all([
        Customer(first_name="Alice", last_name="Martin", email="alice.martin@example.com", phone="+1 555 0111",
                 date_of_birth=date(1988, 4, 12), city="Springfield", country="USA",
                 driver_license_number="D1234567", license_country="USA", license_expiry=date(2030, 4, 12)),
        Customer(first_name="Karim", last_name="Benali", email="karim.benali@example.com", phone="+1 555 0122",
                 date_of_birth=date(1993, 9, 3), city="Springfield", country="USA",
                 driver_license_number="D7654321", license_country="Morocco", license_expiry=date(2031, 1, 20)),
    ])
    log.info("Seeded demo branches, cars and customers")


def main() -> None:
    with SessionLocal() as db:
        ensure_admin(db)
        if settings.seed_demo_data:
            seed_demo(db)
        db.commit()


if __name__ == "__main__":
    main()
