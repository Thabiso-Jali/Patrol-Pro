from sqlalchemy.orm import Session

from .. import models, schemas
from ..domain.corrections import CorrectionCommand
from ..domain.errors import ImmutableRecord
from ..domain.registry import DomainObjectType
from .corrections import emit_correction_event, validate_correction_target
from .domain_registry import register_domain_object
from .tenant_validation import aggregate_mutation, require_tenant_record
from .concurrency import advance_version, lock_tenant_record


def update_patrol_occurrence(
    db: Session, *, patrol_id: int, payload: schemas.PatrolCreate,
    actor_user_id: int, organisation_id: int,
    expected_version: int | None = None,
):
    patrol = lock_tenant_record(
        db, models.Patrol, record_id=patrol_id, organisation_id=organisation_id,
        relationship='Patrol occurrence', allow_archived=True,
    )
    if patrol.lifecycle_status in {'completed', 'missed', 'cancelled', 'archived'}:
        raise ImmutableRecord('patrol_occurrence', patrol.lifecycle_status)
    with aggregate_mutation(db, 'patrol_occurrences'):
        patrol.name = payload.name
        patrol.description = payload.description
        patrol.start_time = payload.start_time
        patrol.end_time = payload.end_time
        patrol.assigned_to = payload.assigned_to
        patrol.required_officers = payload.required_officers
        patrol.updated_by = actor_user_id
        advance_version(patrol, expected_version)
        db.flush()
    return patrol


def cancel_patrol_occurrence(
    db: Session, *, patrol_id: int, actor_user_id: int, organisation_id: int,
    expected_version: int | None = None,
):
    patrol = lock_tenant_record(
        db, models.Patrol, record_id=patrol_id, organisation_id=organisation_id,
        relationship='Patrol occurrence', allow_archived=True,
    )
    if patrol.lifecycle_status in {'completed', 'missed', 'cancelled', 'archived'}:
        raise ImmutableRecord('patrol_occurrence', patrol.lifecycle_status)
    with aggregate_mutation(db, 'patrol_occurrences'):
        patrol.lifecycle_status = 'cancelled'
        patrol.updated_by = actor_user_id
        advance_version(patrol, expected_version)
        db.flush()
    return patrol


def amend_patrol_occurrence(
    db: Session, *, patrol_id: int, command: CorrectionCommand,
    name: str | None = None, description: str | None = None,
    start_time=None, end_time=None, required_officers: int | None = None,
):
    original = require_tenant_record(
        db, models.Patrol, record_id=patrol_id,
        organisation_id=command.organisation_id, relationship='Patrol occurrence',
        allow_archived=True,
    )
    validate_correction_target(db, command=command, record=original, object_type=DomainObjectType.PATROL_OCCURRENCE)
    if original.lifecycle_status not in {'completed', 'missed', 'cancelled', 'archived'}:
        raise ImmutableRecord('patrol_occurrence', original.lifecycle_status)
    amendment = models.Patrol(
        organisation_id=command.organisation_id,
        name=name if name is not None else original.name,
        description=description if description is not None else original.description,
        start_time=start_time if start_time is not None else original.start_time,
        end_time=end_time if end_time is not None else original.end_time,
        required_officers=required_officers if required_officers is not None else original.required_officers,
        site_id=original.site_id, template_id=original.template_id, shift_id=original.shift_id,
        lifecycle_status='draft', template_snapshot=original.template_snapshot,
        operational_snapshot=original.operational_snapshot, amendment_of_id=original.id,
    )
    with aggregate_mutation(db, 'patrol_occurrences'):
        db.add(amendment)
        db.flush()
    register_domain_object(
        db, organisation_id=command.organisation_id,
        object_type=DomainObjectType.PATROL_OCCURRENCE, object_id=amendment.id,
    )
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.PATROL_OCCURRENCE,
        record=original, action='patrol_occurrence.amended',
        additional_metadata={'amendment_id': amendment.id},
    )
    return amendment
