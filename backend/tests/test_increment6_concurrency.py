import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models
from backend.app.database import Base
from backend.app.domain.errors import (
    ConcurrentModification, DomainErrorCode, IdempotencyConflict,
    InvalidExpectedVersion, PersistenceFailure,
)
from backend.app.services.concurrency import advance_version, parse_expected_version
from backend.app.services.idempotency import execute_idempotent
from backend.app.services.transactions import transactional


@pytest.fixture()
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def organisation(db, suffix='one'):
    org = models.Organisation(name='Concurrency', slug=f'concurrency-{suffix}-{uuid.uuid4().hex}')
    db.add(org)
    db.commit()
    return org


def test_expected_version_parsing_and_exactly_one_increment(db):
    assert parse_expected_version('W/"2"') == 2
    with pytest.raises(InvalidExpectedVersion):
        parse_expected_version('not-a-version')
    for malformed in ('"2', '2"', 'W/2', 'W/ "2"', '+2', '0', '-1', True):
        with pytest.raises(InvalidExpectedVersion):
            parse_expected_version(malformed)
    org = organisation(db)
    customer = models.Customer(name='Before', organisation_id=org.id, record_version=2)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    with transactional(db, owner='expected-version'):
        customer.name = 'After'
        advance_version(customer, 2)
    assert customer.record_version == 3
    with pytest.raises(ConcurrentModification):
        with transactional(db, owner='stale-version'):
            customer.name = 'Stale'
            advance_version(customer, 2)
    assert db.get(models.Customer, customer.id).record_version == 3
    assert db.get(models.Customer, customer.id).name == 'After'


def test_idempotent_replay_is_single_execution_and_metadata_is_safe(db):
    org = organisation(db)
    calls = []

    def execute():
        customer = models.Customer(name='Only once', organisation_id=org.id)
        db.add(customer)
        db.flush()
        calls.append(customer.id)
        return customer

    with transactional(db, owner='idempotency'):
        first = execute_idempotent(
            db, organisation_id=org.id, actor_user_id=None,
            actor_scope='system:test', command_type='customer.create', key='safe-key-1',
            fingerprint_payload={'name': 'Only once'}, execute=execute,
            replay=lambda metadata: db.get(models.Customer, int(metadata['customer_id'])),
            result_metadata=lambda customer: {'customer_id': customer.id},
        )
    with transactional(db, owner='idempotency-replay'):
        replayed = execute_idempotent(
            db, organisation_id=org.id, actor_user_id=None,
            actor_scope='system:test', command_type='customer.create', key='safe-key-1',
            fingerprint_payload={'name': 'Only once'}, execute=execute,
            replay=lambda metadata: db.get(models.Customer, int(metadata['customer_id'])),
            result_metadata=lambda customer: {'customer_id': customer.id},
        )
    assert first.value.id == replayed.value.id
    assert replayed.replayed is True
    assert calls == [first.value.id]
    ledger = db.query(models.IdempotencyRecord).one()
    assert ledger.response_metadata == {'customer_id': first.value.id}
    assert 'Only once' not in str(ledger.response_metadata)


def test_idempotency_key_reuse_and_tenant_scope(db):
    first_org = organisation(db, 'first')
    second_org = organisation(db, 'second')

    def run(org, payload):
        return execute_idempotent(
            db, organisation_id=org.id, actor_user_id=None,
            actor_scope='system:test', command_type='test.command', key='same-key',
            fingerprint_payload=payload, execute=lambda: payload['value'],
            replay=lambda metadata: metadata['value'],
            result_metadata=lambda value: {'value': value},
        )

    with transactional(db, owner='first-command'):
        run(first_org, {'value': 1})
    with pytest.raises(IdempotencyConflict) as exc_info:
        with transactional(db, owner='reused-command'):
            run(first_org, {'value': 2})
    assert exc_info.value.code == DomainErrorCode.IDEMPOTENCY_KEY_REUSED
    with transactional(db, owner='other-tenant'):
        assert run(second_org, {'value': 2}).value == 2


def test_failed_command_does_not_leave_completed_ledger(db):
    org = organisation(db)
    with pytest.raises(PersistenceFailure):
        with transactional(db, owner='failed-command'):
            execute_idempotent(
                db, organisation_id=org.id, actor_user_id=None,
                actor_scope='system:test', command_type='failure.test', key='retry-key',
                fingerprint_payload={'safe': True},
                execute=lambda: (_ for _ in ()).throw(RuntimeError('expected test failure')),
                replay=lambda metadata: metadata, result_metadata=lambda value: {},
            )
    assert db.query(models.IdempotencyRecord).count() == 0
    with transactional(db, owner='retry-command'):
        result = execute_idempotent(
            db, organisation_id=org.id, actor_user_id=None,
            actor_scope='system:test', command_type='failure.test', key='retry-key',
            fingerprint_payload={'safe': True}, execute=lambda: 'ok',
            replay=lambda metadata: metadata['result'],
            result_metadata=lambda value: {'result': value},
        )
    assert result.value == 'ok'
