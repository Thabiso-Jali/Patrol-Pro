from sqlalchemy.orm import Session

from .. import models
from ..domain.registry import DomainObjectType
from .domain_registry import register_domain_object


def create_compatibility_site_for_customer(
    db: Session, *, customer: models.Customer, actor_user_id: int | None
) -> models.Site:
    """Create the truthful operational location required by the canonical model.

    The legacy Customer address is copied, never moved or deleted. A placeholder
    explicitly signals that the address requires confirmation.
    """
    organisation = db.query(models.Organisation).filter(
        models.Organisation.id == customer.organisation_id
    ).one()
    site = models.Site(
        organisation_id=customer.organisation_id,
        customer_id=customer.id,
        name=f'{customer.name} Primary Site',
        address=customer.address or 'Address pending confirmation',
        timezone=organisation.timezone,
        staffing_requirement=1,
        status='active',
        source_kind='legacy_customer_address',
        created_by=actor_user_id,
        updated_by=actor_user_id,
    )
    db.add(site)
    db.flush()
    register_domain_object(
        db, organisation_id=customer.organisation_id,
        object_type=DomainObjectType.SITE, object_id=site.id,
    )
    return site
