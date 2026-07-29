from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserRole(str, Enum):
    company_owner = 'company_owner'
    administrator = 'administrator'
    manager = 'manager'
    supervisor = 'supervisor'
    employee = 'employee'
    officer = 'officer'
    read_only = 'read_only'


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: UserRole = UserRole.supervisor
    organisation_name: str | None = Field(default=None, min_length=2, max_length=160)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class User(UserBase):
    id: int
    organisation_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class CompanyRegistration(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    business_email: EmailStr
    owner_name: str = Field(min_length=2, max_length=120)
    owner_email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    registration_number: str | None = Field(default=None, max_length=120)
    vat_number: str | None = Field(default=None, max_length=120)
    tax_number: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=120)
    timezone: str = Field(default='UTC', min_length=1, max_length=80)
    industry: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=64)
    subscription_plan: str = Field(default='pilot', min_length=2, max_length=64)

    @model_validator(mode='before')
    @classmethod
    def support_previous_company_signup_fields(cls, values):
        """Keep existing clients working while treating every signup as a company signup."""
        if not isinstance(values, dict):
            return values
        mapped = dict(values)
        owner_email = mapped.get('owner_email') or mapped.get('email')
        owner_name = mapped.get('owner_name') or mapped.get('full_name')
        company_name = mapped.get('company_name') or mapped.get('organisation_name')
        if not company_name and owner_name:
            company_name = f'{owner_name} Security'
        mapped.setdefault('owner_email', owner_email)
        mapped.setdefault('business_email', owner_email)
        mapped.setdefault('owner_name', owner_name)
        mapped.setdefault('company_name', company_name)
        return mapped


class Company(BaseModel):
    id: int
    name: str
    slug: str
    business_email: EmailStr | None = None
    timezone: str
    subscription_plan: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class RegistrationResult(BaseModel):
    company: Company
    owner: User


class AuthContext(BaseModel):
    user: User
    company: Company
    role: UserRole
    permissions: list[str]


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    access_token_expires_minutes: int


class TokenData(BaseModel):
    email: str | None = None
    role: UserRole | None = None
    user_id: int | None = None
    company_id: int | None = None
    permission_version: int | None = None
    session_version: int | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class EmployeeInvitationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: UserRole


class EmployeeInvitationCreated(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    expires_at: datetime
    invitation_token: str


class EmployeeInvitationAccept(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    password: str = Field(min_length=12, max_length=128)


class MVPLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MVPRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default='officer', min_length=2, max_length=32)


class MVPUser(BaseModel):
    id: int
    name: str | None = None
    email: EmailStr
    role: str
    model_config = ConfigDict(from_attributes=True)


class PatrolBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    assigned_to: str | None = Field(default=None, max_length=120)


class PatrolCreate(PatrolBase):
    pass


class Patrol(PatrolBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class PatrolLogCreate(BaseModel):
    location: str = Field(min_length=2, max_length=240)
    status: str = Field(default='completed', min_length=2, max_length=32)
    timestamp: datetime | None = None


class PatrolLog(BaseModel):
    id: int
    user_id: int
    location: str
    timestamp: datetime
    status: str
    model_config = ConfigDict(from_attributes=True)


class IncidentCreate(BaseModel):
    description: str = Field(min_length=2, max_length=3000)
    severity: str = Field(default='medium', min_length=2, max_length=32)
    timestamp: datetime | None = None


class Incident(BaseModel):
    id: int
    user_id: int
    description: str
    severity: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


class DeviceBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    serial_number: str = Field(min_length=2, max_length=120)
    status: str | None = 'active'


class DeviceCreate(DeviceBase):
    pass


class Device(DeviceBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class CustomerBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    contact_email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=500)


class CustomerCreate(CustomerBase):
    pass


class Customer(CustomerBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class AlertBase(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    severity: str = Field(min_length=2, max_length=32)
    status: str | None = 'open'
    reported_at: datetime
    patrol_id: int | None = None
    device_id: int | None = None
    customer_id: int | None = None


class AlertCreate(AlertBase):
    pass


class Alert(AlertBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class CheckpointBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=120)
    patrol_id: int | None = None
    location_label: str | None = Field(default=None, max_length=240)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    nfc_tag: str | None = Field(default=None, max_length=120)
    status: str = Field(default='pending', min_length=2, max_length=32)


class CheckpointCreate(CheckpointBase):
    pass


class CheckpointVerify(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=120)
    nfc_tag: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Checkpoint(CheckpointBase):
    id: int
    verified_at: datetime | None = None
    verified_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class OfficerLocationCreate(BaseModel):
    patrol_id: int | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=10000)
    battery_level: int | None = Field(default=None, ge=0, le=100)
    recorded_at: datetime | None = None


class OfficerLocation(BaseModel):
    id: int
    officer_user_id: int
    patrol_id: int | None = None
    latitude: float
    longitude: float
    accuracy_meters: float | None = None
    battery_level: int | None = None
    recorded_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NotificationBase(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    body: str | None = Field(default=None, max_length=1000)
    category: str = Field(default='operations', min_length=2, max_length=40)
    priority: str = Field(default='normal', min_length=2, max_length=32)
    recipient_user_id: int | None = None


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase):
    id: int
    read_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class AuditLog(BaseModel):
    id: int
    actor_user_id: int | None = None
    actor_email: EmailStr | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    ip_address: str | None = None
    detail: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OperationsSummary(BaseModel):
    active_patrols: int
    open_incidents: int
    active_devices: int
    customers: int
    officers: int
    pending_checkpoints: int
    unread_notifications: int
    recent_activity: list[AuditLog]


class DashboardActivity(BaseModel):
    action: str
    entity_type: str
    created_at: datetime


class DashboardPatrol(BaseModel):
    id: int
    name: str
    assigned_to: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class DashboardStats(BaseModel):
    active_patrols: int
    officers: int
    open_incidents: int
    pending_checkpoints: int
    completed_checkpoints: int
    checkpoint_completion_rate: int
    recent_activity: list[DashboardActivity]
    active_patrol_details: list[DashboardPatrol]
    todays_schedule: list[DashboardPatrol]


class AnalyticsReport(BaseModel):
    active_patrols: int
    completed_patrols: int
    open_incidents: int
    critical_incidents: int
    pending_checkpoints: int
    verified_checkpoints: int
    active_devices: int
    latest_locations: list[OfficerLocation]
