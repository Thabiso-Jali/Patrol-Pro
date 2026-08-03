from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
import uuid

import pytest

from backend.app import models
from backend.app.database import SessionLocal, engine
from backend.app.domain.corrections import CorrectionCommand
from backend.app.domain.errors import (
    ActiveVersionConflict, ArchiveConflict, ConcurrentModification,
    DomainError, ImmutableRecord,
)
from backend.app.domain.registry import DomainObjectType
from backend.app.services.checkpoint_verifications import confirm_checkpoint
from backend.app.services.concurrency import advance_version, lock_tenant_record
from backend.app.services.company_policies import activate_policy
from backend.app.services.domain_registry import register_domain_object, retire_domain_object
from backend.app.services.evidence import accept_evidence, link_evidence
from backend.app.services.idempotency import execute_idempotent
from backend.app.services.post_orders import activate_post_order_version
from backend.app.services.reports import approve_report
from backend.app.services.shifts import create_shift_draft
from backend.app.services.sites import archive_site
from backend.app.services.tenant_validation import aggregate_mutation
from backend.app.services.transactions import transactional


pytestmark = pytest.mark.skipif(
    engine.dialect.name != 'postgresql', reason='Requires real PostgreSQL row locks',
)


def foundation():
    db = SessionLocal()
    marker = uuid.uuid4().hex
    with transactional(db, owner='race-foundation'):
        org = models.Organisation(name='Race', slug=f'race-{marker}', timezone='UTC')
        db.add(org)
        db.flush()
        user = models.User(
            email=f'{marker}@example.invalid', full_name='Race Employee',
            staff_identifier=f'RACE-{marker[:8]}', hashed_password='placeholder-hash',
            role='employee', organisation_id=org.id,
        )
        db.add(user)
        db.flush()
        employee = models.Employee(
            organisation_id=org.id, user_id=user.id,
            employee_identifier=user.staff_identifier, display_name='Race Employee',
            status='active', source_kind='native',
        )
        with aggregate_mutation(db, 'employees'):
            db.add(employee)
            db.flush()
        customer = models.Customer(name='Race Customer', organisation_id=org.id)
        db.add(customer)
        db.flush()
        site = models.Site(
            organisation_id=org.id, customer_id=customer.id, name=f'Race Site {marker}',
            address='1 Race Road', timezone='UTC', status='active', source_kind='native',
        )
        with aggregate_mutation(db, 'sites'):
            db.add(site)
            db.flush()
        checkpoint = models.Checkpoint(
            name='Race checkpoint', code=f'RACE-{marker}', status='pending',
            organisation_id=org.id,
        )
        db.add(checkpoint)
        db.flush()
        result = org.id, user.id, employee.id, customer.id, checkpoint.id, site.id
    db.close()
    return result


def test_same_expected_version_has_one_authoritative_winner():
    org_id, _, _, customer_id, _, _ = foundation()
    barrier = Barrier(2)

    def writer(name):
        db = SessionLocal()
        try:
            barrier.wait()
            with transactional(db, owner=f'writer-{name}'):
                customer = lock_tenant_record(
                    db, models.Customer, record_id=customer_id,
                    organisation_id=org_id, relationship='Customer',
                )
                advance_version(customer, 1)
                customer.name = name
            return 'won'
        except ConcurrentModification:
            return 'stale'
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(writer, ('Writer A', 'Writer B')))
    assert sorted(outcomes) == ['stale', 'won']
    db = SessionLocal()
    customer = db.get(models.Customer, customer_id)
    assert customer.record_version == 2
    assert customer.name in {'Writer A', 'Writer B'}
    db.close()


def test_concurrent_checkpoint_retry_creates_one_verification():
    org_id, user_id, employee_id, _, checkpoint_id, _ = foundation()
    barrier = Barrier(2)

    def confirmer():
        db = SessionLocal()
        try:
            checkpoint = db.query(models.Checkpoint).filter_by(
                id=checkpoint_id, organisation_id=org_id,
            ).one()
            barrier.wait()
            with transactional(db, owner='checkpoint-race'):
                event = confirm_checkpoint(
                    db, checkpoint=checkpoint, employee_id=employee_id,
                    actor_user_id=user_id, occurred_at=datetime.now(timezone.utc),
                    verification_method='code', idempotency_key='checkpoint-race-key',
                )
                return event.id
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        event_ids = list(pool.map(lambda _: confirmer(), range(2)))
    assert event_ids[0] == event_ids[1]
    db = SessionLocal()
    assert db.query(models.CheckpointVerificationEvent).filter_by(
        organisation_id=org_id, checkpoint_id=checkpoint_id,
    ).count() == 1
    assert db.query(models.IdempotencyRecord).filter_by(
        organisation_id=org_id, command_type='checkpoint.confirm',
    ).count() == 1
    db.close()


def correction(org_id, user_id, employee_id, target_type, target_id, permission, version=1):
    return CorrectionCommand(
        target_type=target_type, target_id=target_id,
        correction_type='controlled_transition', reason_code='RACE_TEST',
        explanation='Exercise deterministic concurrent command handling.',
        actor_user_id=user_id, actor_employee_id=employee_id,
        organisation_id=org_id, permission=permission,
        granted_permissions=frozenset({permission}),
        correlation_id=f'race-{uuid.uuid4().hex}', expected_record_version=version,
    )


def run_pair(worker):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(lambda value: worker(value, barrier), range(2)))


@pytest.mark.parametrize('kind', ['policy', 'post_order'])
def test_concurrent_active_version_activation_has_one_winner(kind):
    org_id, user_id, employee_id, _, _, site_id = foundation()
    setup = SessionLocal()
    with transactional(setup, owner=f'{kind}-setup'):
        if kind == 'policy':
            rows = [models.CompanyPolicy(
                organisation_id=org_id, policy_type='staffing', version=index,
                status='approved', policy_data={'version': index},
            ) for index in (1, 2)]
            service = activate_policy
            target_type = DomainObjectType.COMPANY_POLICY
            permission = 'company.manage'
        else:
            root = models.PostOrder(
                organisation_id=org_id, site_id=site_id, title='Race Orders', status='draft',
            )
            with aggregate_mutation(setup, 'post_orders'):
                setup.add(root)
                setup.flush()
            rows = [models.PostOrderVersion(
                organisation_id=org_id, post_order_id=root.id, version=index,
                status='approved', content=f'Version {index}',
            ) for index in (1, 2)]
            service = activate_post_order_version
            target_type = DomainObjectType.POST_ORDER
            permission = 'company.manage'
        with aggregate_mutation(setup, 'company_policies' if kind == 'policy' else 'post_orders'):
            setup.add_all(rows)
            setup.flush()
        ids = [row.id for row in rows]
        root_id = rows[0].id if kind == 'policy' else root.id
    setup.close()

    def worker(index, barrier):
        db = SessionLocal()
        try:
            command = correction(
                org_id, user_id, employee_id, target_type,
                ids[index] if kind == 'policy' else root_id, permission,
            )
            barrier.wait()
            with transactional(db, owner=f'{kind}-activate-{index}'):
                if kind == 'policy':
                    service(db, policy_id=ids[index], command=command)
                else:
                    service(db, version_id=ids[index], command=command)
            return 'won'
        except (ActiveVersionConflict, ConcurrentModification, DomainError):
            return 'conflict'
        finally:
            db.close()

    outcomes = run_pair(worker)
    assert sorted(outcomes) == ['conflict', 'won']
    db = SessionLocal()
    model = models.CompanyPolicy if kind == 'policy' else models.PostOrderVersion
    assert db.query(model).filter(
        model.organisation_id == org_id, model.status == 'active',
    ).count() == 1
    db.close()


def test_repeated_evidence_acceptance_has_one_authoritative_result():
    org_id, _, employee_id, _, _, _ = foundation()
    setup = SessionLocal()
    with transactional(setup, owner='evidence-setup'):
        evidence = models.EvidenceAttachment(
            organisation_id=org_id, storage_key=f'race/{uuid.uuid4().hex}',
            original_filename='race.txt', media_type='text/plain', byte_size=4,
            content_hash=uuid.uuid4().hex, status='uploading',
        )
        with aggregate_mutation(setup, 'evidence'):
            setup.add(evidence)
            setup.flush()
        evidence_id = evidence.id
    setup.close()

    def worker(_, barrier):
        db = SessionLocal()
        try:
            barrier.wait()
            with transactional(db, owner='evidence-accept-race'):
                return accept_evidence(
                    db, evidence_id=evidence_id, organisation_id=org_id,
                    actor_employee_id=employee_id, expected_version=1,
                    idempotency_key='evidence-accept-race',
                ).id
        finally:
            db.close()

    ids = run_pair(worker)
    assert ids == [evidence_id, evidence_id]
    db = SessionLocal()
    evidence = db.get(models.EvidenceAttachment, evidence_id)
    assert evidence.status == 'available' and evidence.record_version == 2
    assert db.query(models.IdempotencyRecord).filter_by(
        organisation_id=org_id, command_type='evidence.accept',
    ).count() == 1
    db.close()


def test_concurrent_report_approval_has_one_event_and_replay():
    org_id, user_id, employee_id, _, _, site_id = foundation()
    setup = SessionLocal()
    with transactional(setup, owner='report-setup'):
        report = models.DailyActivityReport(
            organisation_id=org_id, site_id=site_id,
            report_key=f'race-{uuid.uuid4().hex}', report_date=datetime.now(timezone.utc).date(),
            revision=1, status='generated', content={'safe': True},
        )
        with aggregate_mutation(setup, 'daily_activity_reports'):
            setup.add(report)
            setup.flush()
        report_id = report.id
    setup.close()

    def worker(_, barrier):
        db = SessionLocal()
        try:
            command = correction(
                org_id, user_id, employee_id, DomainObjectType.DAILY_ACTIVITY_REPORT,
                report_id, 'reports.manage',
            )
            barrier.wait()
            with transactional(db, owner='report-approve-race'):
                return approve_report(
                    db, report_id=report_id, command=command,
                    idempotency_key='report-approve-race',
                ).id
        finally:
            db.close()

    ids = run_pair(worker)
    assert ids == [report_id, report_id]
    db = SessionLocal()
    assert db.query(models.AuditLog).filter_by(
        organisation_id=org_id, action='daily_activity_report.approved',
    ).count() == 1
    db.close()


def test_registry_retirement_vs_evidence_link_is_atomic():
    org_id, user_id, employee_id, customer_id, _, _ = foundation()
    setup = SessionLocal()
    with transactional(setup, owner='registry-race-setup'):
        registered = register_domain_object(
            setup, organisation_id=org_id,
            object_type=DomainObjectType.CUSTOMER, object_id=customer_id,
        )
        evidence = models.EvidenceAttachment(
            organisation_id=org_id, storage_key=f'registry/{uuid.uuid4().hex}',
            original_filename='race.txt', media_type='text/plain', byte_size=4,
            content_hash=uuid.uuid4().hex, status='pending',
        )
        with aggregate_mutation(setup, 'evidence'):
            setup.add(evidence)
            setup.flush()
        registry_id, evidence_id = registered.id, evidence.id
    setup.close()

    def worker(index, barrier):
        db = SessionLocal()
        try:
            barrier.wait()
            with transactional(db, owner=f'registry-race-{index}'):
                if index == 0:
                    command = correction(
                        org_id, user_id, employee_id, DomainObjectType.CUSTOMER,
                        customer_id, 'company.manage',
                    )
                    retire_domain_object(
                        db, organisation_id=org_id,
                        domain_object_id=registry_id, command=command,
                    )
                    return 'retired'
                link_evidence(
                    db, organisation_id=org_id, evidence_attachment_id=evidence_id,
                    domain_object_id=registry_id, linked_by_employee_id=employee_id,
                )
                return 'linked'
        except (ArchiveConflict, DomainError):
            return 'conflict'
        finally:
            db.close()

    outcomes = run_pair(worker)
    assert outcomes.count('conflict') == 1
    db = SessionLocal()
    registered = db.get(models.DomainObject, registry_id)
    links = db.query(models.EvidenceLink).filter_by(domain_object_id=registry_id).count()
    assert (registered.retired_at is not None, links) in {(True, 0), (False, 1)}
    db.close()


def test_site_archive_vs_new_operational_child_has_one_winner():
    org_id, user_id, _, _, _, site_id = foundation()
    barrier = Barrier(2)
    starts_at = datetime.now(timezone.utc)

    def worker(index):
        db = SessionLocal()
        try:
            barrier.wait()
            with transactional(db, owner=f'site-race-{index}'):
                if index == 0:
                    archive_site(
                        db, organisation_id=org_id, site_id=site_id,
                        actor_user_id=user_id, expected_version=1,
                    )
                    return 'archived'
                create_shift_draft(
                    db, organisation_id=org_id, site_id=site_id,
                    name='Concurrent shift', starts_at=starts_at,
                    ends_at=starts_at + timedelta(hours=1),
                )
                return 'created'
        except DomainError:
            return 'conflict'
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, range(2)))
    assert outcomes.count('conflict') == 1
    db = SessionLocal()
    site = db.get(models.Site, site_id)
    shifts = db.query(models.Shift).filter_by(site_id=site_id).count()
    assert (site.status, shifts) in {('archived', 0), ('active', 1)}
    db.close()


def test_concurrent_idempotency_key_reuse_with_different_payload_is_rejected():
    org_id, user_id, _, _, _, _ = foundation()
    barrier = Barrier(2)

    def worker(value):
        db = SessionLocal()
        try:
            barrier.wait()
            with transactional(db, owner=f'idempotency-reuse-{value}'):
                result = execute_idempotent(
                    db, organisation_id=org_id, actor_user_id=user_id,
                    command_type='race.key_reuse', key='shared-different-payload-key',
                    fingerprint_payload={'value': value}, execute=lambda: value,
                    replay=lambda metadata: metadata['value'],
                    result_metadata=lambda result_value: {'value': result_value},
                )
                return ('won', result.value)
        except DomainError as exc:
            return (exc.code.value, None)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, (1, 2)))
    assert sum(outcome[0] == 'won' for outcome in outcomes) == 1
    assert sum(outcome[0] == 'IDEMPOTENCY_KEY_REUSED' for outcome in outcomes) == 1
