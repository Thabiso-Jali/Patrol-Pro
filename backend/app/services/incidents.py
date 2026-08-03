from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..domain.corrections import CorrectionCommand
from ..domain.errors import ConcurrentModification, CorrectionReasonRequired, ImmutableRecord
from ..domain.immutability import approved_correction
from ..domain.registry import DomainObjectType
from .corrections import emit_correction_event, validate_correction_target
from .tenant_validation import aggregate_mutation, require_tenant_record
from .concurrency import advance_version, lock_tenant_record
from .idempotency import execute_idempotent


def create_incident(db: Session, *, payload: schemas.AlertCreate, actor_user_id: int, organisation_id: int):
    return crud.create_alert(
        db, alert=payload, actor_user_id=actor_user_id, organisation_id=organisation_id,
    )


def update_incident(
    db: Session, *, incident_id: int, payload: schemas.AlertCreate,
    actor_user_id: int, organisation_id: int, expected_version: int | None = None,
):
    incident = lock_tenant_record(
        db, models.Alert, record_id=incident_id, organisation_id=organisation_id,
        relationship='Incident', allow_archived=True,
    )
    if incident.status in {'resolved', 'cancelled'}:
        raise ImmutableRecord('incident', incident.status)
    with aggregate_mutation(db, 'incidents'):
        incident.title = payload.title
        incident.description = payload.description
        incident.category = payload.category
        incident.location = payload.location
        incident.resolution_notes = payload.resolution_notes
        incident.severity = payload.severity
        incident.status = payload.status
        incident.reported_at = payload.reported_at
        incident.patrol_id = payload.patrol_id
        incident.device_id = payload.device_id
        incident.customer_id = payload.customer_id
        incident.updated_by = actor_user_id
        advance_version(incident, expected_version)
        db.flush()
    return incident


def _reopen_incident(db: Session, *, incident_id: int, command: CorrectionCommand):
    incident = lock_tenant_record(
        db, models.Alert, record_id=incident_id,
        organisation_id=command.organisation_id, relationship='Incident',
        allow_archived=True,
    )
    validate_correction_target(db, command=command, record=incident, object_type=DomainObjectType.INCIDENT)
    if incident.status not in {'resolved', 'cancelled'}:
        raise ImmutableRecord('incident', incident.status)
    if command.expected_state is None or command.expected_state != incident.status:
        raise ConcurrentModification(incident.record_version)
    if not command.explanation.strip():
        raise CorrectionReasonRequired()
    previous = incident.status
    with aggregate_mutation(db, 'incidents'):
        with approved_correction(db, incident, command):
            incident.status = 'investigating'
            advance_version(incident, command.expected_record_version, required=True)
            db.flush()
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.INCIDENT,
        record=incident, action='incident.reopened',
        additional_metadata={'previous_state': previous, 'new_state': 'investigating'},
    )
    return incident


def reopen_incident(
    db: Session, *, incident_id: int, command: CorrectionCommand,
    idempotency_key: str | None = None,
):
    result = execute_idempotent(
        db, organisation_id=command.organisation_id,
        actor_user_id=command.actor_user_id, actor_scope=(
            f'employee:{command.actor_employee_id}' if command.actor_user_id is None else None
        ), command_type='incident.reopen', key=idempotency_key,
        fingerprint_payload={
            'incident_id': incident_id, 'expected_version': command.expected_record_version,
            'expected_state': command.expected_state, 'reason_code': command.reason_code,
        }, execute=lambda: _reopen_incident(db, incident_id=incident_id, command=command),
        replay=lambda metadata: lock_tenant_record(
            db, models.Alert, record_id=int(metadata['incident_id']),
            organisation_id=command.organisation_id, relationship='Incident',
        ), result_metadata=lambda incident: {
            'incident_id': incident.id, 'status': incident.status,
            'record_version': incident.record_version,
        },
    )
    return result.value


def archive_incident(db: Session, *, incident_id: int, actor_user_id: int, organisation_id: int,
                     expected_version: int | None = None):
    incident = lock_tenant_record(
        db, models.Alert, record_id=incident_id, organisation_id=organisation_id,
        relationship='Incident', allow_archived=True,
    )
    if incident.status in {'resolved', 'cancelled'}:
        raise ImmutableRecord('incident', incident.status)
    with aggregate_mutation(db, 'incidents'):
        incident.status = 'cancelled'
        incident.resolution_notes = 'Cancelled through the legacy compatibility action.'
        incident.updated_by = actor_user_id
        advance_version(incident, expected_version)
        db.flush()
    return incident
