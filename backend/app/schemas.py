from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    admin = 'admin'
    supervisor = 'supervisor'
    officer = 'officer'


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


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    access_token_expires_minutes: int


class TokenData(BaseModel):
    email: str | None = None
    role: UserRole | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


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


class AnalyticsReport(BaseModel):
    active_patrols: int
    completed_patrols: int
    open_incidents: int
    critical_incidents: int
    pending_checkpoints: int
    verified_checkpoints: int
    active_devices: int
    latest_locations: list[OfficerLocation]
