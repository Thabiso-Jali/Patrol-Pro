from datetime import datetime

from sqlalchemy.orm import Session

from .. import models
from .tenant_validation import aggregate_mutation, require_tenant_record


def require_employee(db: Session, *, organisation_id: int, employee_id: int) -> models.Employee:
    return require_tenant_record(
        db, models.Employee, record_id=employee_id,
        organisation_id=organisation_id, relationship='Employee',
    )


def assign_qualification(
    db: Session,
    *,
    organisation_id: int,
    employee_id: int,
    qualification_id: int,
    awarded_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> models.EmployeeQualification:
    require_employee(db, organisation_id=organisation_id, employee_id=employee_id)
    qualification = require_tenant_record(
        db, models.Qualification, record_id=qualification_id,
        organisation_id=organisation_id, relationship='EmployeeQualification.qualification_id',
    )
    if qualification.status != 'active':
        raise ValueError('Qualification does not exist in this organisation')
    if expires_at and awarded_at and expires_at <= awarded_at:
        raise ValueError('Qualification expiry must be after its award')
    assignment = models.EmployeeQualification(
        organisation_id=organisation_id,
        employee_id=employee_id,
        qualification_id=qualification_id,
        status='valid',
        awarded_at=awarded_at,
        expires_at=expires_at,
    )
    with aggregate_mutation(db, 'workforce_credentials'):
        db.add(assignment)
        db.flush()
    return assignment


def record_licence(
    db: Session,
    *,
    organisation_id: int,
    employee_id: int,
    licence_type: str,
    licence_identifier: str,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    qualification_id: int | None = None,
) -> models.Licence:
    require_employee(db, organisation_id=organisation_id, employee_id=employee_id)
    if qualification_id is not None:
        qualification = require_tenant_record(
            db, models.Qualification, record_id=qualification_id,
            organisation_id=organisation_id, relationship='Licence.qualification_id',
        )
        if qualification.status != 'active':
            raise ValueError('Qualification does not exist in this organisation')
    if expires_at and issued_at and expires_at <= issued_at:
        raise ValueError('Licence expiry must be after its issue date')
    licence = models.Licence(
        organisation_id=organisation_id,
        employee_id=employee_id,
        qualification_id=qualification_id,
        licence_type=licence_type,
        licence_identifier=licence_identifier,
        issued_at=issued_at,
        expires_at=expires_at,
        status='pending',
    )
    with aggregate_mutation(db, 'workforce_credentials'):
        db.add(licence)
        db.flush()
    return licence
