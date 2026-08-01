from sqlalchemy.orm import Session

from .. import models
from ..domain.registry import DOMAIN_OBJECT_OWNERS, DomainObjectType


def register_domain_object(
    db: Session,
    *,
    organisation_id: int,
    object_type: DomainObjectType,
    object_id: int,
    aggregate_root_id: int | None = None,
) -> models.DomainObject:
    root_type, service = DOMAIN_OBJECT_OWNERS[object_type]
    existing = db.query(models.DomainObject).filter(
        models.DomainObject.organisation_id == organisation_id,
        models.DomainObject.object_type == object_type.value,
        models.DomainObject.object_id == object_id,
    ).first()
    if existing:
        return existing
    registered = models.DomainObject(
        organisation_id=organisation_id,
        object_type=object_type.value,
        object_id=object_id,
        aggregate_root_type=root_type,
        aggregate_root_id=aggregate_root_id or object_id,
        owning_service=service,
    )
    db.add(registered)
    db.flush()
    return registered


def require_domain_object(
    db: Session, *, organisation_id: int, domain_object_id: int
) -> models.DomainObject:
    registered = db.query(models.DomainObject).filter(
        models.DomainObject.id == domain_object_id,
        models.DomainObject.organisation_id == organisation_id,
        models.DomainObject.retired_at.is_(None),
    ).first()
    if not registered:
        raise ValueError('Domain object does not exist in this organisation')
    return registered
