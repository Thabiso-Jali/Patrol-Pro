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
) -> None:
    entry = models.AuditLog(
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        detail=detail,
    )
    db.add(entry)
    db.commit()
