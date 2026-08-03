import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models
from backend.app.database import Base
from backend.app.domain.errors import DomainError, DomainErrorCode
from backend.app.domain.registry import DomainObjectType
from backend.app.services.domain_registry import register_domain_object, require_domain_object
from backend.app.services.sites import create_compatibility_site_for_customer
from backend.app.services.tenant_validation import aggregate_mutation, assert_aggregate_owner


@pytest.fixture()
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    engine.dispose()


def organisation(db, name):
    record = models.Organisation(name=name, slug=name.lower(), timezone='UTC')
    db.add(record)
    db.flush()
    return record


def customer(db, organisation_id, name='Customer', **values):
    record = models.Customer(name=name, organisation_id=organisation_id, **values)
    db.add(record)
    db.flush()
    return record


def assert_domain_error(exc, code):
    assert exc.value.code == code
    exc.value.__traceback__ = None


def test_flush_rejects_cross_tenant_parent_even_without_endpoint_validation(db):
    first = organisation(db, 'First')
    second = organisation(db, 'Second')
    foreign_customer = customer(db, second.id)
    site = models.Site(
        organisation_id=first.id, customer_id=foreign_customer.id,
        name='Invalid Site', address='1 Road', timezone='UTC', status='active',
    )
    with pytest.raises(DomainError) as exc, aggregate_mutation(db, 'sites'):
        db.add(site)
        db.flush()
    assert_domain_error(exc, DomainErrorCode.CROSS_TENANT_REFERENCE)


def test_flush_rejects_cross_tenant_legacy_team_membership(db):
    first = organisation(db, 'MembershipOne')
    second = organisation(db, 'MembershipTwo')
    user = models.User(
        email='foreign@example.test', full_name='Foreign', staff_identifier='F-1',
        hashed_password='not-a-real-secret', role='officer', organisation_id=second.id,
    )
    team = models.Team(name='Local Team', organisation_id=first.id)
    db.add_all((user, team))
    db.flush()
    db.add(models.TeamMember(
        organisation_id=first.id, team_id=team.id, user_id=user.id,
    ))
    with pytest.raises(DomainError) as exc:
        db.flush()
    assert_domain_error(exc, DomainErrorCode.CROSS_TENANT_REFERENCE)


def test_archived_and_deleted_parents_cannot_receive_new_children(db):
    org = organisation(db, 'Lifecycle')
    archived_customer = customer(db, org.id, is_deleted=True)
    site = models.Site(
        organisation_id=org.id, customer_id=archived_customer.id,
        name='Deleted Parent', address='1 Road', timezone='UTC', status='active',
    )
    with pytest.raises(DomainError) as deleted, aggregate_mutation(db, 'sites'):
        db.add(site)
        db.flush()
    assert_domain_error(deleted, DomainErrorCode.DELETED_OBJECT_REFERENCE)
    db.rollback()

    org = organisation(db, 'ArchivedLifecycle')
    active_customer = customer(db, org.id)
    archived_site = models.Site(
        organisation_id=org.id, customer_id=active_customer.id,
        name='Archived Site', address='2 Road', timezone='UTC', status='archived',
    )
    with aggregate_mutation(db, 'sites'):
        db.add(archived_site)
        db.flush()
    asset = models.SiteAsset(
        organisation_id=org.id, site_id=archived_site.id,
        asset_type='gate', asset_identifier='G-1', name='Gate', status='active',
    )
    with pytest.raises(DomainError) as archived, aggregate_mutation(db, 'sites'):
        db.add(asset)
        db.flush()
    assert_domain_error(archived, DomainErrorCode.ARCHIVED_OBJECT_REFERENCE)


def test_aggregate_mutation_requires_the_canonical_owning_service(db):
    org = organisation(db, 'Ownership')
    local_customer = customer(db, org.id)
    site = models.Site(
        organisation_id=org.id, customer_id=local_customer.id,
        name='Owned Site', address='1 Road', timezone='UTC', status='active',
    )
    db.add(site)
    with pytest.raises(DomainError) as missing_scope:
        db.flush()
    assert_domain_error(missing_scope, DomainErrorCode.AGGREGATE_OWNERSHIP_VIOLATION)
    db.rollback()

    with pytest.raises(DomainError) as wrong_service:
        assert_aggregate_owner(models.Site, 'employees')
    assert_domain_error(wrong_service, DomainErrorCode.AGGREGATE_OWNERSHIP_VIOLATION)


def test_bulk_mutation_cannot_bypass_record_level_tenant_validation(db):
    org = organisation(db, 'BulkSafety')
    customer(db, org.id)
    with pytest.raises(DomainError) as exc:
        db.query(models.Customer).update({'name': 'Bypassed'})
    assert_domain_error(exc, DomainErrorCode.AGGREGATE_OWNERSHIP_VIOLATION)


def test_registry_rejects_orphans_invalid_ownership_and_cross_tenant_lookup(db):
    first = organisation(db, 'RegistryOne')
    second = organisation(db, 'RegistryTwo')
    orphan = models.DomainObject(
        organisation_id=first.id, object_type='site', object_id=99999,
        aggregate_root_type='site', aggregate_root_id=99999, owning_service='sites',
    )
    with pytest.raises(DomainError) as orphaned, aggregate_mutation(db, 'domain_registry'):
        db.add(orphan)
        db.flush()
    assert_domain_error(orphaned, DomainErrorCode.ORPHANED_DOMAIN_OBJECT)
    db.rollback()

    first = organisation(db, 'RegistryOneAgain')
    second = organisation(db, 'RegistryTwoAgain')
    registered = register_domain_object(
        db, organisation_id=first.id,
        object_type=DomainObjectType.ORGANISATION, object_id=first.id,
    )
    with pytest.raises(DomainError) as cross_tenant:
        require_domain_object(db, organisation_id=second.id, domain_object_id=registered.id)
    assert_domain_error(cross_tenant, DomainErrorCode.DOMAIN_OBJECT_NOT_REGISTERED)


def test_registry_rejects_duplicate_and_archived_source_registration(db):
    org = organisation(db, 'RegistryIntegrity')
    local_customer = customer(db, org.id)
    registered = register_domain_object(
        db, organisation_id=org.id,
        object_type=DomainObjectType.CUSTOMER, object_id=local_customer.id,
    )
    duplicate = models.DomainObject(
        organisation_id=org.id, object_type='customer', object_id=local_customer.id,
        aggregate_root_type='customer', aggregate_root_id=local_customer.id,
        owning_service='customers',
    )
    with pytest.raises(DomainError) as duplicate_error, aggregate_mutation(db, 'domain_registry'):
        db.add(duplicate)
        db.flush()
    assert_domain_error(duplicate_error, DomainErrorCode.DUPLICATE_DOMAIN_REGISTRATION)
    db.rollback()

    org = organisation(db, 'ArchivedRegistry')
    archived_customer = customer(db, org.id, is_deleted=True)
    with pytest.raises(DomainError) as archived:
        register_domain_object(
            db, organisation_id=org.id,
            object_type=DomainObjectType.CUSTOMER, object_id=archived_customer.id,
        )
    assert_domain_error(archived, DomainErrorCode.DELETED_OBJECT_REFERENCE)


def test_registry_rejects_noncanonical_aggregate_ownership_metadata(db):
    org = organisation(db, 'RegistryOwnership')
    local_customer = customer(db, org.id)
    invalid = models.DomainObject(
        organisation_id=org.id, object_type='customer', object_id=local_customer.id,
        aggregate_root_type='site', aggregate_root_id=local_customer.id,
        owning_service='sites',
    )
    with pytest.raises(DomainError) as exc, aggregate_mutation(db, 'domain_registry'):
        db.add(invalid)
        db.flush()
    assert_domain_error(exc, DomainErrorCode.AGGREGATE_OWNERSHIP_VIOLATION)


def test_compatibility_bridge_requires_trusted_tenant_context(db):
    first = organisation(db, 'BridgeOne')
    second = organisation(db, 'BridgeTwo')
    foreign_customer = customer(db, second.id)
    with pytest.raises(DomainError) as exc:
        create_compatibility_site_for_customer(
            db, organisation_id=first.id,
            customer=foreign_customer, actor_user_id=None,
        )
    assert_domain_error(exc, DomainErrorCode.CROSS_TENANT_REFERENCE)
