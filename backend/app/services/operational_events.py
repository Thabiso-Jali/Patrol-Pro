from sqlalchemy.orm import Session

from .. import models
from ..domain.corrections import CorrectionCommand
from ..domain.errors import CorrectionCycle, DomainError, DomainErrorCode, InvalidCorrectionTarget
from ..domain.registry import DomainObjectType
from .domain_registry import require_domain_object
from .tenant_validation import aggregate_mutation
from .transactions import require_transaction


_SENSITIVE_METADATA_KEYS = {'password', 'token', 'secret', 'authorization', 'cookie', 'credential'}


def _validate_metadata(metadata: dict | None) -> None:
    if metadata and any(any(sensitive in str(key).lower() for sensitive in _SENSITIVE_METADATA_KEYS) for key in metadata):
        raise DomainError(
            DomainErrorCode.UNSUPPORTED_COMPATIBILITY_WRITE,
            'Operational event metadata contains a prohibited sensitive field.',
            status_code=422,
        )


def append_operational_event(
    db: Session,
    *,
    organisation_id: int,
    action: str,
    actor_user_id: int | None = None,
    actor_employee_id: int | None = None,
    actor_email: str | None = None,
    domain_object_id: int | None = None,
    subject_domain_object_ids: tuple[int, ...] = (),
    event_metadata: dict | None = None,
    visibility: str = 'restricted',
    correlation_id: str | None = None,
    ip_address: str | None = None,
    correction_of_id: int | None = None,
) -> models.AuditLog:
    _validate_metadata(event_metadata)
    primary = None
    if domain_object_id is not None:
        primary = require_domain_object(
            db, organisation_id=organisation_id, domain_object_id=domain_object_id
        )
    for subject_id in subject_domain_object_ids:
        require_domain_object(db, organisation_id=organisation_id, domain_object_id=subject_id)
    event = models.AuditLog(
        organisation_id=organisation_id,
        actor_user_id=actor_user_id,
        actor_employee_id=actor_employee_id,
        actor_email=actor_email,
        action=action,
        entity_type=primary.object_type if primary else 'system',
        entity_id=str(primary.object_id) if primary else None,
        domain_object_id=domain_object_id,
        event_kind='operational',
        event_metadata=event_metadata,
        visibility=visibility,
        correlation_id=correlation_id,
        correction_of_id=correction_of_id,
        ip_address=ip_address,
    )
    with aggregate_mutation(db, 'operational_events'):
        db.add(event)
        db.flush()
        for subject_id in dict.fromkeys(subject_domain_object_ids):
            if subject_id == domain_object_id:
                continue
            db.add(models.OperationalEventSubject(
                organisation_id=organisation_id,
                operational_event_id=event.id,
                domain_object_id=subject_id,
            ))
        db.flush()
    return event


def correct_operational_event(
    db: Session, *, original_event_id: int, command: CorrectionCommand,
    action: str, event_metadata: dict | None = None,
    visibility: str | None = None,
):
    require_transaction(db)
    command.validate()
    original = db.query(models.AuditLog).filter(
        models.AuditLog.id == original_event_id,
        models.AuditLog.organisation_id == command.organisation_id,
    ).one_or_none()
    if original is None:
        raise InvalidCorrectionTarget()
    registered = db.query(models.DomainObject).filter(
        models.DomainObject.organisation_id == command.organisation_id,
        models.DomainObject.object_type == DomainObjectType(command.target_type).value,
        models.DomainObject.object_id == command.target_id,
        models.DomainObject.retired_at.is_(None),
    ).one_or_none()
    if registered is None or registered.id != original.domain_object_id:
        raise InvalidCorrectionTarget()
    seen = {original.id}
    cursor = original
    while cursor.correction_of_id is not None:
        if cursor.correction_of_id in seen:
            raise CorrectionCycle()
        seen.add(cursor.correction_of_id)
        cursor = db.query(models.AuditLog).filter(
            models.AuditLog.id == cursor.correction_of_id,
            models.AuditLog.organisation_id == command.organisation_id,
        ).one_or_none()
        if cursor is None:
            raise InvalidCorrectionTarget()
    ranks = {'public': 0, 'internal': 1, 'restricted': 2, 'security': 3}
    corrected_visibility = visibility or original.visibility
    if ranks.get(corrected_visibility, -1) < ranks.get(original.visibility, 2):
        raise DomainError(
            DomainErrorCode.UNSUPPORTED_COMPATIBILITY_WRITE,
            'Operational event visibility cannot be weakened by a correction.',
        )
    metadata = command.event_metadata()
    metadata.update(event_metadata or {})
    return append_operational_event(
        db, organisation_id=command.organisation_id, action=action,
        actor_user_id=command.actor_user_id, actor_employee_id=command.actor_employee_id,
        domain_object_id=registered.id, event_metadata=metadata,
        visibility=corrected_visibility, correlation_id=command.correlation_id,
        correction_of_id=original.id,
    )
