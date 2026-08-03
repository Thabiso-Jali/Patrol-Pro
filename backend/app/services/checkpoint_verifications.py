from datetime import datetime

from sqlalchemy.orm import Session

from .. import models
from ..domain.corrections import CorrectionCommand
from ..domain.errors import CorrectionCycle
from ..domain.registry import DomainObjectType
from ..domain.immutability import approved_projection
from .corrections import emit_correction_event, validate_correction_target
from .domain_registry import register_domain_object
from .tenant_validation import aggregate_mutation, require_tenant_record
from .transactions import require_transaction
from .concurrency import lock_tenant_record
from .idempotency import execute_idempotent


def record_checkpoint_verification(
    db: Session,
    *,
    organisation_id: int,
    checkpoint_id: int,
    employee_id: int,
    occurred_at: datetime,
    verification_method: str,
    result: str,
    patrol_occurrence_id: int | None = None,
    shift_id: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> models.CheckpointVerificationEvent:
    require_transaction(db)
    event = models.CheckpointVerificationEvent(
        organisation_id=organisation_id,
        checkpoint_id=checkpoint_id,
        patrol_occurrence_id=patrol_occurrence_id,
        employee_id=employee_id,
        shift_id=shift_id,
        occurred_at=occurred_at,
        verification_method=verification_method,
        result=result,
        latitude=latitude,
        longitude=longitude,
        event_kind='original',
        record_provenance=(
            'legacy_low_assurance' if verification_method.startswith('legacy')
            else 'native_confirmation'
        ),
    )
    with aggregate_mutation(db, 'checkpoint_verifications'):
        db.add(event)
        db.flush()
    register_domain_object(
        db, organisation_id=organisation_id,
        object_type=DomainObjectType.CHECKPOINT_VERIFICATION, object_id=event.id,
    )
    return event


def confirm_checkpoint(
    db: Session, *, checkpoint: models.Checkpoint, employee_id: int,
    actor_user_id: int, occurred_at: datetime, verification_method: str,
    latitude: float | None = None, longitude: float | None = None,
    idempotency_key: str | None = None,
):
    require_transaction(db)
    organisation_id = checkpoint.organisation_id

    def execute():
        locked = lock_tenant_record(
            db, models.Checkpoint, record_id=checkpoint.id,
            organisation_id=organisation_id, relationship='Checkpoint',
        )
        if locked.status == 'verified':
            from ..domain.errors import DomainError, DomainErrorCode
            raise DomainError(
                DomainErrorCode.DUPLICATE_VERIFICATION,
                'This checkpoint confirmation has already been accepted.',
            )
        if locked.status == 'inactive':
            from ..domain.errors import InvalidObjectReference
            raise InvalidObjectReference('Checkpoint', archived=True)
        with approved_projection(db, locked):
            locked.status = 'verified'
            locked.verified_at = occurred_at
            locked.verified_by = actor_user_id
            locked.updated_by = actor_user_id
            event = record_checkpoint_verification(
                db, organisation_id=organisation_id, checkpoint_id=locked.id,
                patrol_occurrence_id=locked.patrol_id, employee_id=employee_id,
                occurred_at=occurred_at, verification_method=verification_method,
                result='accepted', latitude=latitude, longitude=longitude,
            )
            db.flush()
        return event

    result = execute_idempotent(
        db, organisation_id=organisation_id, actor_user_id=actor_user_id,
        command_type='checkpoint.confirm', key=idempotency_key,
        fingerprint_payload={
            'checkpoint_id': checkpoint.id, 'employee_id': employee_id,
            'method': verification_method, 'latitude': latitude, 'longitude': longitude,
        },
        execute=execute,
        replay=lambda metadata: require_tenant_record(
            db, models.CheckpointVerificationEvent,
            record_id=int(metadata['verification_event_id']),
            organisation_id=organisation_id, relationship='Verification event',
            allow_archived=True,
        ),
        result_metadata=lambda event: {
            'verification_event_id': event.id, 'checkpoint_id': event.checkpoint_id,
            'result': event.result,
        },
    )
    return result.value


def correct_checkpoint_verification(
    db: Session, *, original_event_id: int, command: CorrectionCommand,
    result: str, verification_method: str | None = None,
):
    original = require_tenant_record(
        db, models.CheckpointVerificationEvent, record_id=original_event_id,
        organisation_id=command.organisation_id, relationship='Verification event',
        allow_archived=True,
    )
    validate_correction_target(
        db, command=command, record=original,
        object_type=DomainObjectType.CHECKPOINT_VERIFICATION,
    )
    seen = {original.id}
    cursor = original
    while cursor.correction_of_id is not None:
        if cursor.correction_of_id in seen:
            raise CorrectionCycle()
        seen.add(cursor.correction_of_id)
        cursor = require_tenant_record(
            db, models.CheckpointVerificationEvent, record_id=cursor.correction_of_id,
            organisation_id=command.organisation_id, relationship='Verification correction',
            allow_archived=True,
        )
    root_id = original.original_event_id or original.id
    correction = models.CheckpointVerificationEvent(
        organisation_id=command.organisation_id,
        checkpoint_id=original.checkpoint_id,
        patrol_occurrence_id=original.patrol_occurrence_id,
        employee_id=command.actor_employee_id or original.employee_id,
        shift_id=original.shift_id,
        occurred_at=datetime.now(original.occurred_at.tzinfo) if original.occurred_at.tzinfo else datetime.now(),
        verification_method=verification_method or original.verification_method,
        result=result,
        event_kind='correction', correction_of_id=original.id,
        original_event_id=root_id, record_provenance='controlled_correction',
        context_snapshot={'reason_code': command.reason_code},
    )
    with aggregate_mutation(db, 'checkpoint_verifications'):
        db.add(correction)
        db.flush()
    register_domain_object(
        db, organisation_id=command.organisation_id,
        object_type=DomainObjectType.CHECKPOINT_VERIFICATION, object_id=correction.id,
    )
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.CHECKPOINT_VERIFICATION,
        record=original, action='checkpoint_verification.corrected',
        additional_metadata={'correction_event_id': correction.id, 'original_event_id': root_id},
    )
    return correction
