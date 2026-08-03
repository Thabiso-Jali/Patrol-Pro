from sqlalchemy.orm import Session

from .. import models
from ..domain.corrections import CorrectionCommand
from ..domain.errors import ImmutableRecord
from ..domain.registry import DomainObjectType
from .corrections import emit_correction_event, validate_correction_target
from .domain_registry import register_domain_object
from .tenant_validation import aggregate_mutation, require_tenant_record
from .concurrency import lock_tenant_record
from .transactions import require_transaction


def create_shift_draft(
    db: Session, *, organisation_id: int, site_id: int, name: str,
    starts_at, ends_at,
) -> models.Shift:
    """Internal Shift aggregate command; public workflow remains intentionally absent."""
    require_transaction(db)
    lock_tenant_record(
        db, models.Site, record_id=site_id, organisation_id=organisation_id,
        relationship='Shift.site_id', allow_archived=False,
    )
    shift = models.Shift(
        organisation_id=organisation_id, site_id=site_id, name=name,
        starts_at=starts_at, ends_at=ends_at, status='draft',
    )
    with aggregate_mutation(db, 'shifts'):
        db.add(shift)
        db.flush()
    register_domain_object(
        db, organisation_id=organisation_id,
        object_type=DomainObjectType.SHIFT, object_id=shift.id,
    )
    return shift


def amend_shift(
    db: Session, *, shift_id: int, command: CorrectionCommand,
    name: str | None = None, site_id: int | None = None,
    starts_at=None, ends_at=None,
):
    original = require_tenant_record(
        db, models.Shift, record_id=shift_id, organisation_id=command.organisation_id,
        relationship='Shift', allow_archived=True,
    )
    validate_correction_target(db, command=command, record=original, object_type=DomainObjectType.SHIFT)
    if original.status not in {'completed', 'cancelled', 'archived'}:
        raise ImmutableRecord('shift', original.status)
    target_site = site_id if site_id is not None else original.site_id
    require_tenant_record(
        db, models.Site, record_id=target_site, organisation_id=command.organisation_id,
        relationship='Shift amendment site',
    )
    amendment = models.Shift(
        organisation_id=command.organisation_id,
        site_id=target_site,
        name=name if name is not None else original.name,
        starts_at=starts_at if starts_at is not None else original.starts_at,
        ends_at=ends_at if ends_at is not None else original.ends_at,
        status='draft', amendment_of_id=original.id,
    )
    with aggregate_mutation(db, 'shifts'):
        db.add(amendment)
        db.flush()
    register_domain_object(
        db, organisation_id=command.organisation_id,
        object_type=DomainObjectType.SHIFT, object_id=amendment.id,
    )
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.SHIFT,
        record=original, action='shift.amended',
        additional_metadata={'amendment_id': amendment.id},
    )
    return amendment


def amend_shift_assignment(
    db: Session, *, assignment_id: int, command: CorrectionCommand,
    employee_id: int | None = None, team_id: int | None = None,
):
    original = require_tenant_record(
        db, models.ShiftAssignment, record_id=assignment_id,
        organisation_id=command.organisation_id, relationship='Shift assignment',
        allow_archived=True,
    )
    if original.status not in {'completed', 'cancelled'}:
        raise ImmutableRecord('shift_assignment', original.status)
    # Assignments are owned by the Shift aggregate; the correction targets that root.
    shift = require_tenant_record(
        db, models.Shift, record_id=original.shift_id,
        organisation_id=command.organisation_id, relationship='Shift', allow_archived=True,
    )
    validate_correction_target(db, command=command, record=shift, object_type=DomainObjectType.SHIFT)
    replacement = models.ShiftAssignment(
        organisation_id=command.organisation_id, shift_id=original.shift_id,
        employee_id=(employee_id if employee_id is not None else (None if team_id is not None else original.employee_id)),
        team_id=(team_id if team_id is not None else (None if employee_id is not None else original.team_id)),
        status='proposed',
    )
    with aggregate_mutation(db, 'shifts'):
        db.add(replacement)
        db.flush()
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.SHIFT,
        record=shift, action='shift_assignment.corrected',
        additional_metadata={'original_assignment_id': original.id, 'replacement_assignment_id': replacement.id},
    )
    return replacement
