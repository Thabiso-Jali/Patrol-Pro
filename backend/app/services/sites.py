from sqlalchemy.orm import Session

from .. import models
from ..domain.registry import DomainObjectType
from .domain_registry import register_domain_object
from .tenant_validation import aggregate_mutation, require_tenant_record
from .concurrency import advance_version, lock_tenant_record
from .transactions import require_transaction
from ..domain.errors import ArchiveConflict


def create_compatibility_site_for_customer(
    db: Session, *, organisation_id: int, customer: models.Customer, actor_user_id: int | None
) -> models.Site:
    """Create the truthful operational location required by the canonical model.

    The legacy Customer address is copied, never moved or deleted. A placeholder
    explicitly signals that the address requires confirmation.
    """
    customer = require_tenant_record(
        db, models.Customer, record_id=customer.id,
        organisation_id=organisation_id, relationship='CompatibilitySite.customer_id',
    )
    organisation = require_tenant_record(
        db, models.Organisation, record_id=organisation_id,
        organisation_id=organisation_id, relationship='CompatibilitySite.organisation_id',
    )
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
    with aggregate_mutation(db, 'sites'):
        db.add(site)
        db.flush()
    register_domain_object(
        db, organisation_id=customer.organisation_id,
        object_type=DomainObjectType.SITE, object_id=site.id,
    )
    return site


def archive_site(
    db: Session, *, organisation_id: int, site_id: int,
    actor_user_id: int | None, expected_version: int | None,
) -> models.Site:
    """Internal Site aggregate command; no public API is introduced."""
    require_transaction(db)
    site = lock_tenant_record(
        db, models.Site, record_id=site_id, organisation_id=organisation_id,
        relationship='Site', allow_archived=False,
    )
    active_child = any((
        db.query(models.Shift.id).filter(
            models.Shift.organisation_id == organisation_id, models.Shift.site_id == site.id,
            models.Shift.status.in_({'draft', 'published', 'active'}),
        ).with_for_update().first(),
        db.query(models.Patrol.id).filter(
            models.Patrol.organisation_id == organisation_id, models.Patrol.site_id == site.id,
            models.Patrol.lifecycle_status.in_({'draft', 'scheduled', 'in_progress'}),
        ).with_for_update().first(),
    ))
    if active_child:
        raise ArchiveConflict()
    with aggregate_mutation(db, 'sites'):
        site.status = 'archived'
        site.updated_by = actor_user_id
        advance_version(site, expected_version)
        db.flush()
    return site
