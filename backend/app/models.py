from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer,
    JSON, String, Text, UniqueConstraint, text,
)
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
    business_email = Column(String, nullable=True)
    registration_number = Column(String, nullable=True)
    vat_number = Column(String, nullable=True)
    tax_number = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    country = Column(String, nullable=True)
    timezone = Column(String, nullable=False, default='UTC')
    industry = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    subscription_plan = Column(String, nullable=False, default='pilot')
    permission_version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default='active', index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class User(Base, AuditMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    staff_identifier = Column(String, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default='officer', index=True)
    role_migrated_from_admin = Column(Boolean, nullable=False, default=False)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    session_version = Column(Integer, nullable=False, default=1)
    permission_version = Column(Integer, nullable=False, default=1)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True, index=True)
    last_login_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint('organisation_id', 'staff_identifier', name='uq_users_org_staff_identifier'),
    )


class Patrol(Base, AuditMixin):
    __tablename__ = 'patrols'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    assigned_to = Column(String, nullable=True)
    required_officers = Column(Integer, nullable=False, default=1)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=True, index=True)
    template_id = Column(Integer, ForeignKey('patrol_templates.id'), nullable=True, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=True, index=True)
    lifecycle_status = Column(String, nullable=False, default='scheduled', index=True)
    template_snapshot = Column(JSON, nullable=True)
    amendment_of_id = Column(Integer, ForeignKey('patrols.id'), nullable=True, index=True)
    record_version = Column(Integer, nullable=False, default=1)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class Team(Base, AuditMixin):
    __tablename__ = 'teams'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'name', name='uq_teams_org_name'),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    leader_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='active', index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class TeamMember(Base):
    __tablename__ = 'team_members'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'user_id', name='uq_team_members_org_user'),
        UniqueConstraint('team_id', 'user_id', name='uq_team_members_team_user'),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, nullable=True, index=True)


class PatrolAssignment(Base):
    __tablename__ = 'patrol_assignments'
    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND team_id IS NULL) OR '
            '(user_id IS NULL AND team_id IS NOT NULL)',
            name='ck_patrol_assignment_one_target',
        ),
        UniqueConstraint('patrol_id', 'user_id', name='uq_patrol_assignment_user'),
        UniqueConstraint('patrol_id', 'team_id', name='uq_patrol_assignment_team'),
    )

    id = Column(Integer, primary_key=True, index=True)
    patrol_id = Column(Integer, ForeignKey('patrols.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True, index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, nullable=True, index=True)


class PatrolLog(Base):
    __tablename__ = 'patrol_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    location = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=utcnow, index=True)
    status = Column(String, nullable=False, default='completed', index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class Incident(Base):
    __tablename__ = 'incidents'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    description = Column(String, nullable=False)
    severity = Column(String, nullable=False, default='medium', index=True)
    timestamp = Column(DateTime, nullable=False, default=utcnow, index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class Device(Base, AuditMixin):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    serial_number = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default='active')
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class Customer(Base, AuditMixin):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    commercial_metadata = Column(JSON, nullable=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class Alert(Base, AuditMixin):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False, default='security', index=True)
    location = Column(String, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False, default='open')
    reported_at = Column(DateTime, nullable=False)
    patrol_id = Column(Integer, ForeignKey('patrols.id'), nullable=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    reported_by = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=True, index=True)
    patrol_occurrence_id = Column(Integer, ForeignKey('patrols.id'), nullable=True, index=True)
    source_kind = Column(String, nullable=False, default='native', index=True)
    source_id = Column(String, nullable=True, index=True)
    record_version = Column(Integer, nullable=False, default=1)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class Checkpoint(Base, AuditMixin):
    __tablename__ = 'checkpoints'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'code', name='uq_checkpoints_org_code'),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False, index=True)
    patrol_id = Column(Integer, ForeignKey('patrols.id'), nullable=True, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=True, index=True)
    location_label = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    nfc_tag = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default='pending', index=True)
    verified_at = Column(DateTime, nullable=True, index=True)
    verified_by = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


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
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class Notification(Base, AuditMixin):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=True)
    category = Column(String, nullable=False, default='operations', index=True)
    priority = Column(String, nullable=False, default='normal', index=True)
    recipient_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    read_at = Column(DateTime, nullable=True, index=True)
    domain_object_id = Column(Integer, ForeignKey('domain_objects.id'), nullable=True, index=True)
    channel = Column(String, nullable=False, default='in_app', index=True)
    delivery_status = Column(String, nullable=False, default='queued', index=True)
    delivered_at = Column(DateTime, nullable=True, index=True)
    failed_at = Column(DateTime, nullable=True, index=True)
    failure_code = Column(String, nullable=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, nullable=True, index=True)
    actor_email = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=True, index=True)
    domain_object_id = Column(Integer, ForeignKey('domain_objects.id'), nullable=True, index=True)
    actor_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True, index=True)
    event_kind = Column(String, nullable=False, default='audit', index=True)
    event_metadata = Column(JSON, nullable=True)
    visibility = Column(String, nullable=False, default='restricted', index=True)
    correlation_id = Column(String, nullable=True, index=True)
    correction_of_id = Column(Integer, ForeignKey('audit_logs.id'), nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    detail = Column(String, nullable=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class EmployeeInvitation(Base):
    __tablename__ = 'employee_invitations'
    __table_args__ = (
        Index(
            'uq_active_invitation_company_email',
            'organisation_id',
            'email',
            unique=True,
            postgresql_where=text('accepted_at IS NULL'),
            sqlite_where=text('accepted_at IS NULL'),
        ),
    )

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    accepted_at = Column(DateTime, nullable=True, index=True)
    invited_by = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class DomainObject(Base):
    """Shared registry for every polymorphic domain reference."""
    __tablename__ = 'domain_objects'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'object_type', 'object_id', name='uq_domain_object_identity'),
    )
    __aggregate_root__ = 'organisation'
    __owning_service__ = 'domain_registry'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    object_type = Column(String, nullable=False, index=True)
    object_id = Column(Integer, nullable=False, index=True)
    aggregate_root_type = Column(String, nullable=False, index=True)
    aggregate_root_id = Column(Integer, nullable=False, index=True)
    owning_service = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    retired_at = Column(DateTime, nullable=True, index=True)


class Employee(Base, AuditMixin):
    __tablename__ = 'employees'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'employee_identifier', name='uq_employees_org_identifier'),
        UniqueConstraint('user_id', name='uq_employees_user'),
    )
    __aggregate_root__ = 'employee'
    __owning_service__ = 'employees'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    employee_identifier = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    employment_role = Column(String, nullable=False, default='security_officer', index=True)
    status = Column(String, nullable=False, default='active', index=True)
    source_kind = Column(String, nullable=False, default='native', index=True)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)


class Contact(Base, AuditMixin):
    __tablename__ = 'contacts'
    __table_args__ = (
        CheckConstraint(
            '(customer_id IS NOT NULL AND site_id IS NULL) OR '
            '(customer_id IS NULL AND site_id IS NOT NULL)',
            name='ck_contact_one_owner',
        ),
    )
    __aggregate_root__ = 'customer_or_site'
    __owning_service__ = 'contacts'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=True, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=True, index=True)
    contact_type = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    role_title = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)


class Site(Base, AuditMixin):
    __tablename__ = 'sites'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'customer_id', 'name', name='uq_sites_customer_name'),
    )
    __aggregate_root__ = 'site'
    __owning_service__ = 'sites'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    address = Column(Text, nullable=False)
    timezone = Column(String, nullable=False, default='UTC')
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    staffing_requirement = Column(Integer, nullable=False, default=1)
    instructions = Column(Text, nullable=True)
    operational_risk = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='active', index=True)
    source_kind = Column(String, nullable=False, default='native', index=True)


class SiteAsset(Base, AuditMixin):
    __tablename__ = 'site_assets'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'site_id', 'asset_identifier', name='uq_site_asset_identifier'),
    )
    __aggregate_root__ = 'site'
    __owning_service__ = 'sites'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False, index=True)
    parent_asset_id = Column(Integer, ForeignKey('site_assets.id'), nullable=True, index=True)
    asset_type = Column(String, nullable=False, index=True)
    asset_identifier = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    location_label = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='active', index=True)
    retired_at = Column(DateTime, nullable=True)


class CompanyPolicy(Base, AuditMixin):
    __tablename__ = 'company_policies'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'policy_type', 'version', name='uq_company_policy_version'),
    )
    __aggregate_root__ = 'organisation'
    __owning_service__ = 'company_policies'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    policy_type = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default='draft', index=True)
    policy_data = Column(JSON, nullable=False, default=dict)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    supersedes_id = Column(Integer, ForeignKey('company_policies.id'), nullable=True, index=True)
    approved_by_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)


class PostOrder(Base, AuditMixin):
    __tablename__ = 'post_orders'
    __aggregate_root__ = 'site'
    __owning_service__ = 'post_orders'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False, default='general', index=True)
    status = Column(String, nullable=False, default='draft', index=True)


class PostOrderVersion(Base):
    __tablename__ = 'post_order_versions'
    __table_args__ = (UniqueConstraint('post_order_id', 'version', name='uq_post_order_version'),)
    __aggregate_root__ = 'site'
    __owning_service__ = 'post_orders'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    post_order_id = Column(Integer, ForeignKey('post_orders.id'), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default='draft', index=True)
    content = Column(Text, nullable=False)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    supersedes_id = Column(Integer, ForeignKey('post_order_versions.id'), nullable=True)
    created_by_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    approved_by_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    approved_at = Column(DateTime, nullable=True)


class PostOrderAcknowledgement(Base):
    __tablename__ = 'post_order_acknowledgements'
    __table_args__ = (
        UniqueConstraint('post_order_version_id', 'employee_id', name='uq_post_order_ack_employee'),
    )
    __aggregate_root__ = 'site'
    __owning_service__ = 'post_orders'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    post_order_version_id = Column(Integer, ForeignKey('post_order_versions.id'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=False, default=utcnow)
    acknowledgement_context = Column(JSON, nullable=True)


class Qualification(Base, AuditMixin):
    __tablename__ = 'qualifications'
    __table_args__ = (UniqueConstraint('organisation_id', 'code', name='uq_qualification_code'),)
    __aggregate_root__ = 'organisation'
    __owning_service__ = 'workforce_credentials'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='active', index=True)


class EmployeeQualification(Base):
    __tablename__ = 'employee_qualifications'
    __table_args__ = (UniqueConstraint('employee_id', 'qualification_id', name='uq_employee_qualification'),)
    __aggregate_root__ = 'employee'
    __owning_service__ = 'workforce_credentials'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False, index=True)
    qualification_id = Column(Integer, ForeignKey('qualifications.id'), nullable=False, index=True)
    status = Column(String, nullable=False, default='valid', index=True)
    awarded_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class Licence(Base, AuditMixin):
    __tablename__ = 'licences'
    __table_args__ = (UniqueConstraint('organisation_id', 'licence_identifier', name='uq_licence_identifier'),)
    __aggregate_root__ = 'employee'
    __owning_service__ = 'workforce_credentials'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False, index=True)
    qualification_id = Column(Integer, ForeignKey('qualifications.id'), nullable=True)
    licence_type = Column(String, nullable=False, index=True)
    licence_identifier = Column(String, nullable=False, index=True)
    issuer = Column(String, nullable=True)
    issued_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    status = Column(String, nullable=False, default='pending', index=True)


class AvailabilityPeriod(Base, AuditMixin):
    __tablename__ = 'availability_periods'
    __aggregate_root__ = 'employee'
    __owning_service__ = 'workforce_scheduling'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False, index=True)
    starts_at = Column(DateTime, nullable=False, index=True)
    ends_at = Column(DateTime, nullable=False, index=True)
    status = Column(String, nullable=False, default='proposed', index=True)
    recurrence_rule = Column(String, nullable=True)


class LeavePeriod(Base, AuditMixin):
    __tablename__ = 'leave_periods'
    __aggregate_root__ = 'employee'
    __owning_service__ = 'workforce_scheduling'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False, index=True)
    starts_at = Column(DateTime, nullable=False, index=True)
    ends_at = Column(DateTime, nullable=False, index=True)
    leave_type = Column(String, nullable=False, default='other', index=True)
    status = Column(String, nullable=False, default='requested', index=True)
    decided_by_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    decided_at = Column(DateTime, nullable=True)


class Shift(Base, AuditMixin):
    __tablename__ = 'shifts'
    __aggregate_root__ = 'shift'
    __owning_service__ = 'shifts'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False, index=True)
    name = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False, index=True)
    ends_at = Column(DateTime, nullable=False, index=True)
    status = Column(String, nullable=False, default='draft', index=True)
    amendment_of_id = Column(Integer, ForeignKey('shifts.id'), nullable=True)
    record_version = Column(Integer, nullable=False, default=1)


class ShiftAssignment(Base, AuditMixin):
    __tablename__ = 'shift_assignments'
    __table_args__ = (
        CheckConstraint(
            '(employee_id IS NOT NULL AND team_id IS NULL) OR '
            '(employee_id IS NULL AND team_id IS NOT NULL)',
            name='ck_shift_assignment_one_target',
        ),
    )
    __aggregate_root__ = 'shift'
    __owning_service__ = 'shifts'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True, index=True)
    status = Column(String, nullable=False, default='proposed', index=True)


class PatrolTemplate(Base, AuditMixin):
    __tablename__ = 'patrol_templates'
    __aggregate_root__ = 'patrol_template'
    __owning_service__ = 'patrol_templates'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False, index=True)
    name = Column(String, nullable=False)
    route_description = Column(Text, nullable=True)
    required_employees = Column(Integer, nullable=False, default=1)
    expected_duration_minutes = Column(Integer, nullable=False, default=60)
    instructions = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='draft', index=True)
    version = Column(Integer, nullable=False, default=1)
    supersedes_id = Column(Integer, ForeignKey('patrol_templates.id'), nullable=True)


class PatrolTemplateCheckpoint(Base):
    __tablename__ = 'patrol_template_checkpoints'
    __table_args__ = (
        UniqueConstraint('patrol_template_id', 'sequence', name='uq_template_checkpoint_sequence'),
        UniqueConstraint('patrol_template_id', 'checkpoint_id', name='uq_template_checkpoint'),
    )
    __aggregate_root__ = 'patrol_template'
    __owning_service__ = 'patrol_templates'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    patrol_template_id = Column(Integer, ForeignKey('patrol_templates.id'), nullable=False, index=True)
    checkpoint_id = Column(Integer, ForeignKey('checkpoints.id'), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    instructions = Column(Text, nullable=True)


class CheckpointVerificationEvent(Base):
    __tablename__ = 'checkpoint_verification_events'
    __aggregate_root__ = 'patrol_occurrence'
    __owning_service__ = 'checkpoint_verifications'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    checkpoint_id = Column(Integer, ForeignKey('checkpoints.id'), nullable=False, index=True)
    patrol_occurrence_id = Column(Integer, ForeignKey('patrols.id'), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=True, index=True)
    occurred_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    verification_method = Column(String, nullable=False, index=True)
    result = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    source_kind = Column(String, nullable=False, default='native', index=True)


class OperationalAlert(Base, AuditMixin):
    __tablename__ = 'operational_alerts'
    __aggregate_root__ = 'operational_alert'
    __owning_service__ = 'operational_alerts'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    incident_id = Column(Integer, ForeignKey('alerts.id'), nullable=True, index=True)
    domain_object_id = Column(Integer, ForeignKey('domain_objects.id'), nullable=True, index=True)
    title = Column(String, nullable=False)
    severity = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default='open', index=True)
    acknowledged_by_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class EvidenceAttachment(Base):
    __tablename__ = 'evidence_attachments'
    __aggregate_root__ = 'evidence'
    __owning_service__ = 'evidence'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    storage_key = Column(String, nullable=False, unique=True)
    original_filename = Column(String, nullable=False)
    media_type = Column(String, nullable=False, index=True)
    byte_size = Column(Integer, nullable=False)
    content_hash = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default='pending', index=True)
    retention_status = Column(String, nullable=False, default='active', index=True)
    created_by_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    supersedes_id = Column(Integer, ForeignKey('evidence_attachments.id'), nullable=True)


class EvidenceLink(Base):
    __tablename__ = 'evidence_links'
    __table_args__ = (
        UniqueConstraint('evidence_attachment_id', 'domain_object_id', name='uq_evidence_domain_link'),
    )
    __aggregate_root__ = 'evidence'
    __owning_service__ = 'evidence'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    evidence_attachment_id = Column(Integer, ForeignKey('evidence_attachments.id'), nullable=False, index=True)
    domain_object_id = Column(Integer, ForeignKey('domain_objects.id'), nullable=False, index=True)
    linked_at = Column(DateTime, nullable=False, default=utcnow)
    linked_by_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)


class DailyActivityReport(Base):
    __tablename__ = 'daily_activity_reports'
    __table_args__ = (
        UniqueConstraint('organisation_id', 'report_key', 'revision', name='uq_daily_report_revision'),
    )
    __aggregate_root__ = 'daily_activity_report'
    __owning_service__ = 'daily_activity_reports'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False, index=True)
    report_key = Column(String, nullable=False, index=True)
    report_date = Column(DateTime, nullable=False, index=True)
    revision = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default='draft', index=True)
    content = Column(JSON, nullable=False, default=dict)
    supersedes_id = Column(Integer, ForeignKey('daily_activity_reports.id'), nullable=True)
    generated_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_by_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class OperationalEventSubject(Base):
    __tablename__ = 'operational_event_subjects'
    __table_args__ = (
        UniqueConstraint('operational_event_id', 'domain_object_id', name='uq_event_subject'),
    )
    __aggregate_root__ = 'operational_event'
    __owning_service__ = 'operational_events'

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey('organisations.id'), nullable=False, index=True)
    operational_event_id = Column(Integer, ForeignKey('audit_logs.id'), nullable=False, index=True)
    domain_object_id = Column(Integer, ForeignKey('domain_objects.id'), nullable=False, index=True)
