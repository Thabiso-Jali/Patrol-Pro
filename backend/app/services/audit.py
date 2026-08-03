from sqlalchemy.orm import Session

from .. import models
from .tenant_validation import aggregate_mutation


def log_audit_event(
    db: Session,
    *,
    actor_user_id: int | None,
    actor_email: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    ip_address: str | None = None,
    detail: str | None = None,
    organisation_id: int | None = None,
) -> None:
    if organisation_id is None and actor_user_id is not None:
        organisation_id = (
            db.query(models.User.organisation_id)
            .filter(models.User.id == actor_user_id)
            .scalar()
        )
    if organisation_id is None:
        raise ValueError('Audit events require an organisation')
    domain_object_id = None
    if entity_id is not None and entity_id.isdigit():
        domain_object_id = db.query(models.DomainObject.id).filter(
            models.DomainObject.organisation_id == organisation_id,
            models.DomainObject.object_type == entity_type,
            models.DomainObject.object_id == int(entity_id),
        ).scalar()
    actor_employee_id = None
    if actor_user_id is not None:
        actor_employee_id = db.query(models.Employee.id).filter(
            models.Employee.organisation_id == organisation_id,
            models.Employee.user_id == actor_user_id,
        ).scalar()
    entry = models.AuditLog(
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        domain_object_id=domain_object_id,
        actor_employee_id=actor_employee_id,
        event_kind='security' if action.startswith('auth.') else 'operational',
        visibility='restricted',
        ip_address=ip_address,
        detail=detail,
        organisation_id=organisation_id,
    )
    with aggregate_mutation(db, 'operational_events'):
        db.add(entry)
        db.flush()
