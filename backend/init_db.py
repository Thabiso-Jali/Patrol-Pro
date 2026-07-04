#!/usr/bin/env python3
"""
Database initialization script for Patrol Pro.
Creates all tables and optionally seeds demo data.
"""
import sys
from datetime import datetime, timedelta, timezone
from app.database import engine, Base
from app.models import User, Patrol, Device, Customer, Alert
from app.security import get_password_hash
from sqlalchemy.orm import sessionmaker

# Create all tables
Base.metadata.create_all(bind=engine)
print("✓ Database tables created")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Check if demo user exists
    existing_user = db.query(User).filter(User.email == 'officer1783163143325@patrol.pro').first()
    
    if not existing_user:
        # Create demo user
        demo_user = User(
            email='officer1783163143325@patrol.pro',
            full_name='Demo Officer',
            hashed_password=get_password_hash('password123'),
        )
        db.add(demo_user)
        db.commit()
        print("✓ Demo user created: officer1783163143325@patrol.pro / password123")
    else:
        print("✓ Demo user already exists")
    
    # Check if demo patrols exist
    existing_patrols = db.query(Patrol).count()
    if existing_patrols == 0:
        now = datetime.now(timezone.utc)
        demo_patrols = [
            Patrol(
                name='Night Shift - North Zone',
                description='Perimeter patrol covering north sector',
                start_time=now,
                end_time=now + timedelta(hours=8),
                assigned_to='Officer Johnson',
            ),
            Patrol(
                name='Day Shift - South Zone',
                description='Perimeter patrol covering south sector',
                start_time=now + timedelta(hours=8),
                end_time=now + timedelta(hours=16),
                assigned_to='Officer Smith',
            ),
        ]
        for patrol in demo_patrols:
            db.add(patrol)
        db.commit()
        print(f"✓ Created {len(demo_patrols)} demo patrols")
    else:
        print(f"✓ Database already contains {existing_patrols} patrols")
    
    # Check if demo devices exist
    existing_devices = db.query(Device).count()
    if existing_devices == 0:
        demo_devices = [
            Device(
                name='GPS Unit A',
                serial_number='GPS-001',
                status='active',
            ),
            Device(
                name='Radio Unit B',
                serial_number='RADIO-001',
                status='active',
            ),
        ]
        for device in demo_devices:
            db.add(device)
        db.commit()
        print(f"✓ Created {len(demo_devices)} demo devices")
    else:
        print(f"✓ Database already contains {existing_devices} devices")
    
    print("\n✅ Database initialization complete!")
    print("\nYou can now start the backend with:")
    print("  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")

except Exception as e:
    print(f"❌ Error during initialization: {e}")
    sys.exit(1)
finally:
    db.close()
