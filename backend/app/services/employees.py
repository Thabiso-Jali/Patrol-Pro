from sqlalchemy.orm import Session

from .. import models
from ..domain.errors import ArchiveConflict
from .concurrency import advance_version, lock_tenant_record
from .tenant_validation import aggregate_mutation
from .transactions import require_transaction


def employee_for_user(db: Session, *, organisation_id: int, user_id: int) -> models.Employee | None:
    return db.query(models.Employee).filter(
        models.Employee.organisation_id == organisation_id,
        models.Employee.user_id == user_id,
        models.Employee.is_deleted.is_(False),
    ).first()


def archive_employee(
    db: Session, *, organisation_id: int, employee_id: int,
    expected_version: int | None,
) -> models.Employee:
    """Internal workforce command; no public API until the workflow is complete."""
    require_transaction(db)
    employee = lock_tenant_record(
        db, models.Employee, record_id=employee_id,
        organisation_id=organisation_id, relationship='Employee',
        allow_archived=False,
    )
    active_assignment = (
        db.query(models.PatrolAssignment.id).join(
            models.Patrol, models.Patrol.id == models.PatrolAssignment.patrol_id,
        ).filter(
            models.PatrolAssignment.organisation_id == organisation_id,
            models.PatrolAssignment.employee_id == employee.id,
            models.Patrol.lifecycle_status.in_({'draft', 'scheduled', 'in_progress'}),
        ).with_for_update().first()
        or db.query(models.ShiftAssignment.id).filter(
            models.ShiftAssignment.organisation_id == organisation_id,
            models.ShiftAssignment.employee_id == employee.id,
            models.ShiftAssignment.status.in_({'proposed', 'confirmed', 'active'}),
        ).with_for_update().first()
    )
    if active_assignment:
        raise ArchiveConflict()
    with aggregate_mutation(db, 'employees'):
        employee.status = 'archived'
        employee.is_deleted = True
        advance_version(employee, expected_version)
        db.flush()
    return employee
