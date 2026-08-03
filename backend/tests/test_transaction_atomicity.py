from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import crud, models, schemas
from backend.app.database import Base
from backend.app.domain.errors import (
    DomainError, InvalidObjectReference, PersistenceFailure, TransactionOwnershipViolation,
)
from backend.app.domain.registry import DomainObjectType
from backend.app.services.checkpoint_verifications import record_checkpoint_verification
from backend.app.services.domain_registry import register_domain_object
from backend.app.services.operational_events import append_operational_event
from backend.app.services.staffing import replace_patrol_assignments
from backend.app.services.tenant_validation import aggregate_mutation
from backend.app.services.transactions import transactional


@pytest.fixture()
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    engine.dispose()


def create_org(db, name='Atomic'):
    with transactional(db, owner='test.setup'):
        organisation = crud.create_organisation(db, name=name)
    return organisation


def create_user(db, organisation_id, email='employee@example.test'):
    with transactional(db, owner='test.setup'):
        user = crud.create_user(
            db, email=email, full_name='Employee', hashed_password='test-hash',
            organisation_id=organisation_id,
        )
    return user


def test_registration_failure_rolls_back_organisation_registry_and_owner(db):
    with pytest.raises(PersistenceFailure):
        with transactional(db, owner='registration'):
            organisation = crud.create_organisation(db, name='Rollback Registration')
            crud.create_user(
                db, email='owner@example.test', full_name='Owner',
                hashed_password='test-hash', role='company_owner',
                organisation_id=organisation.id,
            )
            raise RuntimeError('event writer unavailable')
    assert db.query(models.Organisation).count() == 0
    assert db.query(models.User).count() == 0
    assert db.query(models.Employee).count() == 0
    assert db.query(models.DomainObject).count() == 0


def test_invitation_acceptance_failure_does_not_consume_invitation_or_create_employee(db):
    organisation = create_org(db, 'Invitation Atomicity')
    owner = create_user(db, organisation.id, 'owner@example.test')
    with transactional(db, owner='test.setup'):
        invitation = models.EmployeeInvitation(
            organisation_id=organisation.id, email='invitee@example.test',
            full_name='Invitee', role='officer', token_hash='fake-token-hash',
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1), invited_by=owner.id,
        )
        db.add(invitation)

    with pytest.raises(PersistenceFailure):
        with transactional(db, owner='invitation.accept'):
            crud.create_user(
                db, email=invitation.email, full_name=invitation.full_name,
                hashed_password='test-hash', role=invitation.role,
                organisation_id=organisation.id,
            )
            raise RuntimeError('failed before invitation consumption')
    db.expire_all()
    assert db.query(models.User).filter_by(email='invitee@example.test').first() is None
    assert db.query(models.EmployeeInvitation).filter_by(id=invitation.id).one().accepted_at is None


def test_registry_failure_rolls_back_owning_business_record(db):
    organisation = create_org(db, 'Registry Atomicity')
    other = create_org(db, 'Other Registry Tenant')
    with pytest.raises(DomainError):
        with transactional(db, owner='customer.create'):
            customer = models.Customer(name='Unregistered', organisation_id=organisation.id)
            db.add(customer)
            db.flush()
            register_domain_object(
                db, organisation_id=other.id,
                object_type=DomainObjectType.CUSTOMER, object_id=customer.id,
            )
    assert db.query(models.Customer).filter_by(name='Unregistered').first() is None


def test_team_member_removal_failure_restores_original_membership(db):
    organisation = create_org(db, 'Team Atomicity')
    member = create_user(db, organisation.id)
    with transactional(db, owner='test.setup'):
        team = models.Team(name='Alpha', organisation_id=organisation.id, leader_user_id=member.id)
        db.add(team)
        db.flush()
        db.add(models.TeamMember(
            organisation_id=organisation.id, team_id=team.id, user_id=member.id,
        ))
    with pytest.raises(PersistenceFailure):
        with transactional(db, owner='team.update'):
            membership = db.query(models.TeamMember).filter_by(team_id=team.id).one()
            db.delete(membership)
            db.flush()
            raise RuntimeError('leader update failed')
    assert db.query(models.TeamMember).filter_by(team_id=team.id, user_id=member.id).one()


def test_patrol_assignment_failure_rolls_back_patrol_and_registry(db):
    organisation = create_org(db, 'Patrol Atomicity')
    now = datetime.now(timezone.utc)
    payload = schemas.PatrolCreate(
        name='Atomic Patrol', start_time=now, end_time=now + timedelta(hours=1),
        required_officers=2, officer_ids=[], team_ids=[],
    )
    with pytest.raises(HTTPException):
        with transactional(db, owner='patrol.create'):
            patrol = crud.create_patrol(db, payload, organisation_id=organisation.id)
            replace_patrol_assignments(db, patrol, [], [], None)
    assert db.query(models.Patrol).filter_by(name='Atomic Patrol').first() is None
    assert db.query(models.DomainObject).filter_by(object_type='patrol_occurrence').first() is None


def test_checkpoint_projection_rolls_back_when_event_relationship_fails(db):
    organisation = create_org(db, 'Checkpoint Atomicity')
    other = create_org(db, 'Checkpoint Other')
    user = create_user(db, organisation.id)
    employee = db.query(models.Employee).filter_by(user_id=user.id).one()
    with transactional(db, owner='test.setup'):
        checkpoint = crud.create_checkpoint(
            db,
            schemas.CheckpointCreate(name='Gate', code='GATE-1', status='pending'),
            organisation_id=organisation.id,
        )
    with pytest.raises(DomainError):
        with transactional(db, owner='checkpoint.verify'):
            crud.verify_checkpoint(
                db, checkpoint.id, schemas.CheckpointVerify(code='GATE-1'),
                actor_user_id=user.id, organisation_id=organisation.id,
            )
            record_checkpoint_verification(
                db, organisation_id=other.id, checkpoint_id=checkpoint.id,
                employee_id=employee.id, occurred_at=datetime.now(timezone.utc),
                verification_method='code', result='accepted',
            )
    db.expire_all()
    checkpoint = db.query(models.Checkpoint).filter_by(id=checkpoint.id).one()
    assert checkpoint.status == 'pending'
    assert checkpoint.verified_at is None
    assert db.query(models.CheckpointVerificationEvent).count() == 0


def test_event_store_failure_rolls_back_incident_and_compatibility_site(db):
    organisation = create_org(db, 'Event Atomicity')
    with pytest.raises(DomainError):
        with transactional(db, owner='customer.create'):
            customer = crud.create_customer(
                db, schemas.CustomerCreate(name='Rollback Customer'),
                organisation_id=organisation.id,
            )
            target = db.query(models.DomainObject).filter_by(
                object_type='customer', object_id=customer.id,
            ).one()
            append_operational_event(
                db, organisation_id=organisation.id, action='customer.created',
                domain_object_id=target.id, subject_domain_object_ids=(999999,),
            )
    assert db.query(models.Customer).filter_by(name='Rollback Customer').first() is None
    assert db.query(models.Site).filter_by(name='Rollback Customer Primary Site').first() is None
    assert db.query(models.AuditLog).filter_by(action='customer.created').first() is None


def test_database_event_write_failure_rolls_back_incident_and_registry(db):
    organisation = create_org(db, 'Incident Atomicity')
    now = datetime.now(timezone.utc)
    with pytest.raises(PersistenceFailure):
        with transactional(db, owner='incident.create'):
            incident = crud.create_alert(
                db,
                schemas.AlertCreate(
                    title='Atomic incident', severity='high', status='open', reported_at=now,
                ),
                organisation_id=organisation.id,
            )
            db.add(models.AuditLog(
                organisation_id=organisation.id,
                action=None,
                entity_type='incident',
                entity_id=str(incident.id),
            ))
            db.flush()
    assert db.query(models.Alert).filter_by(title='Atomic incident').first() is None
    assert db.query(models.DomainObject).filter_by(object_type='incident').first() is None
    assert db.query(models.AuditLog).count() == 0


def test_nested_transaction_is_rejected_and_session_is_reusable_after_rollback(db):
    with pytest.raises(TransactionOwnershipViolation):
        with transactional(db, owner='outer'):
            with transactional(db, owner='inner'):
                pass
    assert not db.info.get('patrol_pro_transaction_owner')
    organisation = create_org(db, 'Retry Works')
    assert db.query(models.Organisation).filter_by(id=organisation.id).one()


def test_domain_errors_and_request_cancellation_roll_back_without_rewriting(db):
    with pytest.raises(InvalidObjectReference) as preserved:
        with transactional(db, owner='domain.failure'):
            db.add(models.Organisation(name='Domain Rollback', slug='domain-rollback'))
            db.flush()
            raise InvalidObjectReference('Customer')
    assert preserved.value.code.value == 'MISSING_REQUIRED_RELATIONSHIP'
    assert db.query(models.Organisation).filter_by(slug='domain-rollback').first() is None

    with pytest.raises(KeyboardInterrupt):
        with transactional(db, owner='cancelled.request'):
            db.add(models.Organisation(name='Cancelled', slug='cancelled'))
            db.flush()
            raise KeyboardInterrupt()
    assert db.query(models.Organisation).filter_by(slug='cancelled').first() is None
