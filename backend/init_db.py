#!/usr/bin/env python3
"""Explicit, idempotent demo-data seeding.

The database schema must already exist via ``alembic upgrade head``. This
command never runs during application startup.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Device, Organisation, Patrol, User
from app.security import get_password_hash

logger = logging.getLogger("patrol_pro.seed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed fake Patrol Pro demo data")
    parser.add_argument(
        "--confirm-demo-data",
        action="store_true",
        help="Explicitly allow seeding outside APP_ENV=demo",
    )
    return parser.parse_args()


def require_demo_credentials() -> tuple[str, str]:
    email = os.getenv("DEMO_ADMIN_EMAIL", "").strip()
    password = os.getenv("DEMO_ADMIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("DEMO_ADMIN_EMAIL and DEMO_ADMIN_PASSWORD are required")
    if len(password) < 12:
        raise RuntimeError("DEMO_ADMIN_PASSWORD must contain at least 12 characters")
    return email, password


def seed_demo_data(db: Session, email: str, password: str) -> None:
    organisation = db.query(Organisation).filter(Organisation.slug == "patrol-pro-demo").first()
    if organisation is None:
        organisation = Organisation(
            name="Patrol Pro Demo Company",
            slug="patrol-pro-demo",
            contact_email=email,
        )
        db.add(organisation)
        db.flush()

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        db.add(
            User(
                email=email,
                full_name="Demo Administrator",
                hashed_password=get_password_hash(password),
                role="admin",
                organisation_id=organisation.id,
            )
        )

    if not db.query(Patrol).filter(Patrol.organisation_id == organisation.id).first():
        now = datetime.now(timezone.utc)
        db.add(
            Patrol(
                name="Demo perimeter patrol",
                description="Synthetic data for product demonstration only",
                start_time=now,
                end_time=now + timedelta(hours=8),
                assigned_to="Demo Officer",
                organisation_id=organisation.id,
            )
        )

    if not db.query(Device).filter(Device.serial_number == "DEMO-GPS-001").first():
        db.add(
            Device(
                name="Demo GPS unit",
                serial_number="DEMO-GPS-001",
                status="active",
                organisation_id=organisation.id,
            )
        )

    db.commit()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    if settings.APP_ENV != "demo" and not args.confirm_demo_data:
        logger.error("Set APP_ENV=demo or pass --confirm-demo-data to seed fake demo data")
        return 2

    try:
        email, password = require_demo_credentials()
        with SessionLocal() as db:
            seed_demo_data(db, email, password)
    except Exception:
        logger.exception("Demo seeding failed")
        return 1

    logger.info("Fake demo data is ready for %s", email)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
