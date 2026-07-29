from sqlalchemy.orm import Session

from .. import models


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
    commit: bool = True,
) -> None:
    if organisation_id is None and actor_user_id is not None:
        organisation_id = (
            db.query(models.User.organisation_id)
            .filter(models.User.id == actor_user_id)
            .scalar()
        )
    if organisation_id is None:
        raise ValueError('Audit events require an organisation')
    entry = models.AuditLog(
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        detail=detail,
        organisation_id=organisation_id,
    )
    db.add(entry)
    if commit:
        db.commit()
