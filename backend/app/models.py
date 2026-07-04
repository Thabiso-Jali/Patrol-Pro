from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class AuditMixin:
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow, index=True)
    created_by = Column(Integer, nullable=True, index=True)
    updated_by = Column(Integer, nullable=True, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)


class Organisation(Base):
    """Top-level tenant entity — one per security company."""
    __tablename__ = 'organisations'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    contact_email = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class User(Base, AuditMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default='officer', index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class Patrol(Base, AuditMixin):
    __tablename__ = 'patrols'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    assigned_to = Column(String, nullable=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class PatrolLog(Base):
    __tablename__ = 'patrol_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    location = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=utcnow, index=True)
    status = Column(String, nullable=False, default='completed', index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class Incident(Base):
    __tablename__ = 'incidents'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    description = Column(String, nullable=False)
    severity = Column(String, nullable=False, default='medium', index=True)
    timestamp = Column(DateTime, nullable=False, default=utcnow, index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class Device(Base, AuditMixin):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    serial_number = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default='active')
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class Customer(Base, AuditMixin):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class Alert(Base, AuditMixin):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False, default='open')
    reported_at = Column(DateTime, nullable=False)
    patrol_id = Column(Integer, ForeignKey('patrols.id'), nullable=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class Checkpoint(Base, AuditMixin):
    __tablename__ = 'checkpoints'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False, index=True)
    patrol_id = Column(Integer, ForeignKey('patrols.id'), nullable=True, index=True)
    location_label = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    nfc_tag = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default='pending', index=True)
    verified_at = Column(DateTime, nullable=True, index=True)
    verified_by = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class OfficerLocation(Base):
    __tablename__ = 'officer_locations'

    id = Column(Integer, primary_key=True, index=True)
    officer_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    patrol_id = Column(Integer, ForeignKey('patrols.id'), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    battery_level = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class Notification(Base, AuditMixin):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=True)
    category = Column(String, nullable=False, default='operations', index=True)
    priority = Column(String, nullable=False, default='normal', index=True)
    recipient_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    read_at = Column(DateTime, nullable=True, index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=True, index=True)


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, nullable=True, index=True)
    actor_email = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    detail = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)
