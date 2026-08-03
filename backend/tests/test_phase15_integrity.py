from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.app import models
from backend.app.database import Base
from backend.app.database import engine as application_engine
from backend.app.domain.states import STATE_MACHINES
from backend.app.domain.errors import CrossTenantReference
from backend.app.services.tenant_validation import aggregate_mutation


@pytest.fixture()
def integrity_db():
    engine = create_engine('sqlite:///:memory:')
    event.listen(engine, 'connect', lambda connection, _record: connection.execute('PRAGMA foreign_keys=ON'))
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def add_org(db, slug):
    organisation = models.Organisation(name=slug, slug=slug, timezone='UTC')
    db.add(organisation)
    db.flush()
    return organisation


def test_integrity_revision_is_single_additive_child_of_phase1():
    revisions = Path('backend/alembic/versions')
    text = (revisions / 'f15a4c9d7e21_add_phase15_integrity_structures.py').read_text()
    assert "revision: str = 'f15a4c9d7e21'" in text
    assert "down_revision: Union[str, Sequence[str], None] = 'c6b03fd24b2a'" in text
    assert "op.drop_table(" not in text.split('def upgrade()', 1)[1].split('def downgrade()', 1)[0]
    assert "op.drop_column(" not in text.split('def upgrade()', 1)[1].split('def downgrade()', 1)[0]


def test_stored_state_constraints_follow_executable_catalogue(integrity_db):
    org = add_org(integrity_db, 'state-check')
    customer = models.Customer(name='Customer', organisation_id=org.id, status='not-a-state')
    integrity_db.add(customer)
    with pytest.raises(IntegrityError):
        integrity_db.flush()
    integrity_db.rollback()
    assert {'active', 'inactive', 'archived'} == STATE_MACHINES['customer'].states


def test_versions_default_to_one_and_append_only_records_are_unversioned(integrity_db):
    org = add_org(integrity_db, 'versions')
    customer = models.Customer(name='Customer', organisation_id=org.id)
    integrity_db.add(customer)
    integrity_db.flush()
    assert org.record_version == customer.record_version == 1
    assert not hasattr(models.CheckpointVerificationEvent, 'record_version')
    assert not hasattr(models.OperationalEventSubject, 'record_version')
    assert not hasattr(models.EvidenceLink, 'record_version')


def test_active_policy_and_post_order_versions_are_unique(integrity_db):
    org = add_org(integrity_db, 'active-versions')
    with aggregate_mutation(integrity_db, 'company_policies'):
        integrity_db.add_all([
            models.CompanyPolicy(
            organisation_id=org.id, policy_type='staffing', version=1,
            status='active', policy_data={},
            ),
            models.CompanyPolicy(
            organisation_id=org.id, policy_type='staffing', version=2,
            status='active', policy_data={},
            ),
        ])
        with pytest.raises(IntegrityError):
            integrity_db.flush()


def test_idempotency_scope_rejects_duplicate_and_different_fingerprint(integrity_db):
    org = add_org(integrity_db, 'idempotency')
    common = dict(
        organisation_id=org.id, actor_scope='system', command_type='patrol.create',
        idempotency_key='replay-key', processing_state='completed',
        correlation_id='correlation', created_at=datetime.now(timezone.utc),
    )
    with aggregate_mutation(integrity_db, 'idempotency'):
        integrity_db.add(models.IdempotencyRecord(request_fingerprint='hash-one', **common))
        integrity_db.flush()
        integrity_db.add(models.IdempotencyRecord(request_fingerprint='hash-two', **common))
        with pytest.raises(IntegrityError):
            integrity_db.flush()


def test_tenant_composite_reference_rejects_cross_tenant_employee(integrity_db):
    first = add_org(integrity_db, 'tenant-one')
    second = add_org(integrity_db, 'tenant-two')
    user = models.User(
        email='employee@example.invalid', full_name='Employee', staff_identifier='EMP-1',
        hashed_password='not-a-real-secret', role='employee', organisation_id=first.id,
    )
    integrity_db.add(user)
    integrity_db.flush()
    employee = models.Employee(
        organisation_id=first.id, user_id=user.id, employee_identifier='EMP-1',
        display_name='Employee', status='active', source_kind='native',
    )
    team = models.Team(name='Other Team', organisation_id=second.id)
    with aggregate_mutation(integrity_db, 'employees'):
        integrity_db.add(employee)
        integrity_db.flush()
    with aggregate_mutation(integrity_db, 'teams'):
        integrity_db.add(team)
        integrity_db.flush()
    integrity_db.add(models.TeamMember(
        organisation_id=second.id, team_id=team.id, user_id=user.id,
        employee_id=employee.id, employee_reference_source='canonical_user_mapping',
    ))
    with pytest.raises((IntegrityError, CrossTenantReference)):
        integrity_db.flush()


def test_verification_self_correction_is_rejected(integrity_db):
    table = models.CheckpointVerificationEvent.__table__
    constraint_names = {constraint.name for constraint in table.constraints}
    assert 'ck_checkpoint_verification_not_self_correction' in constraint_names
    assert 'fk_checkpoint_verification_tenant_correction' in constraint_names


@pytest.mark.skipif(
    application_engine.dialect.name != 'postgresql',
    reason='PostgreSQL is authoritative for migrated partial indexes and composite keys',
)
def test_postgresql_migration_constraints_are_materialised_and_enforced():
    inspector = inspect(application_engine)
    assert 'uq_company_policies_active_scope' in {
        index['name'] for index in inspector.get_indexes('company_policies')
    }
    assert 'uq_post_order_versions_active_scope' in {
        index['name'] for index in inspector.get_indexes('post_order_versions')
    }
    assert 'fk_team_members_tenant_employee' in {
        foreign_key['name'] for foreign_key in inspector.get_foreign_keys('team_members')
    }
    assert 'ck_organisations_status' in {
        constraint['name'] for constraint in inspector.get_check_constraints('organisations')
    }
    with application_engine.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(text("""
                INSERT INTO organisations (
                    name, slug, is_active, created_at, updated_at, timezone,
                    subscription_plan, permission_version, status, record_version
                ) VALUES (
                    'Invalid State Fixture', 'invalid-state-fixture', true,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'UTC', 'pilot', 1,
                    'not-a-state', 1
                )
            """))
