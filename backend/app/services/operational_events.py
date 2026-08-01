from sqlalchemy.orm import Session

from .. import models
from .domain_registry import require_domain_object


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
    return event
