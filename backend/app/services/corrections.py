from sqlalchemy.orm import Session

from ..domain.corrections import CorrectionCommand
from ..domain.errors import ConcurrentModification, InvalidCorrectionTarget
from ..domain.registry import DomainObjectType
from .domain_registry import register_domain_object
from .operational_events import append_operational_event
from .transactions import require_transaction


def validate_correction_target(
    db: Session,
    *,
    command: CorrectionCommand,
    record,
    object_type: DomainObjectType,
):
    require_transaction(db)
    command.validate()
    if DomainObjectType(command.target_type) != object_type:
        raise InvalidCorrectionTarget()
    if record.id != command.target_id or record.organisation_id != command.organisation_id:
        raise InvalidCorrectionTarget()
    if command.expected_record_version is not None:
        current = getattr(record, 'record_version', None)
        if current != command.expected_record_version:
            raise ConcurrentModification(current)


def emit_correction_event(
    db: Session,
    *,
    command: CorrectionCommand,
    object_type: DomainObjectType,
    record,
    action: str,
    correction_of_event_id: int | None = None,
    additional_metadata: dict | None = None,
):
    registered = register_domain_object(
        db,
        organisation_id=command.organisation_id,
        object_type=object_type,
        object_id=record.id,
    )
    metadata = command.event_metadata()
    metadata.update(additional_metadata or {})
    return append_operational_event(
        db,
        organisation_id=command.organisation_id,
        action=action,
        actor_user_id=command.actor_user_id,
        actor_employee_id=command.actor_employee_id,
        domain_object_id=registered.id,
        event_metadata=metadata,
        correlation_id=command.correlation_id,
        correction_of_id=correction_of_event_id,
    )
