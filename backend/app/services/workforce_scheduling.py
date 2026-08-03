from datetime import datetime

from sqlalchemy.orm import Session

from .. import models
from .workforce_credentials import require_employee
from .tenant_validation import aggregate_mutation


def _validate_period(starts_at: datetime, ends_at: datetime) -> None:
    if ends_at <= starts_at:
        raise ValueError('End time must be after start time')


def declare_availability(
    db: Session,
    *,
    organisation_id: int,
    employee_id: int,
    starts_at: datetime,
    ends_at: datetime,
    recurrence_rule: str | None = None,
) -> models.AvailabilityPeriod:
    require_employee(db, organisation_id=organisation_id, employee_id=employee_id)
    _validate_period(starts_at, ends_at)
    period = models.AvailabilityPeriod(
        organisation_id=organisation_id,
        employee_id=employee_id,
        starts_at=starts_at,
        ends_at=ends_at,
        recurrence_rule=recurrence_rule,
        status='proposed',
    )
    with aggregate_mutation(db, 'workforce_scheduling'):
        db.add(period)
        db.flush()
    return period


def request_leave(
    db: Session,
    *,
    organisation_id: int,
    employee_id: int,
    starts_at: datetime,
    ends_at: datetime,
    leave_type: str = 'other',
) -> models.LeavePeriod:
    require_employee(db, organisation_id=organisation_id, employee_id=employee_id)
    _validate_period(starts_at, ends_at)
    leave = models.LeavePeriod(
        organisation_id=organisation_id,
        employee_id=employee_id,
        starts_at=starts_at,
        ends_at=ends_at,
        leave_type=leave_type,
        status='requested',
    )
    with aggregate_mutation(db, 'workforce_scheduling'):
        db.add(leave)
        db.flush()
    return leave
