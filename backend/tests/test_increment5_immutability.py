from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models
from backend.app.database import Base
from backend.app.domain.corrections import CorrectionCommand
from backend.app.domain.errors import (
    CorrectionPermissionRequired, CorrectionReasonRequired, CrossTenantReference,
    HardDeleteForbidden, ImmutableRecord, PersistenceFailure,
)
from backend.app.domain.registry import DomainObjectType
from backend.app.services.company_policies import activate_policy
from backend.app.services.domain_registry import register_domain_object
from backend.app.services.evidence import record_evidence_unlink, replace_evidence
from backend.app.services.incidents import reopen_incident
from backend.app.services.operational_events import append_operational_event, correct_operational_event
from backend.app.services.patrol_occurrences import amend_patrol_occurrence
from backend.app.services.patrol_templates import replace_patrol_template
from backend.app.services.post_orders import (
    activate_post_order_version, approve_post_order_version, create_post_order_draft,
)
from backend.app.services.reports import correct_report
from backend.app.services.shifts import amend_shift, amend_shift_assignment
from backend.app.services.checkpoint_verifications import correct_checkpoint_verification
from backend.app.services.checkpoint_verifications import confirm_checkpoint
from backend.app.services.tenant_validation import aggregate_mutation
from backend.app.services.transactions import transactional


@pytest.fixture()
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def foundation(db, slug='immutable'):
    org = models.Organisation(name=slug, slug=f'{slug}-{uuid.uuid4().hex}', timezone='UTC')
    db.add(org)
    db.flush()
    user = models.User(
        email=f'{uuid.uuid4().hex}@example.invalid', full_name='Controller',
        staff_identifier=f'EMP-{uuid.uuid4().hex[:8]}', hashed_password='placeholder-hash',
        role='company_owner', organisation_id=org.id,
    )
    db.add(user)
    db.flush()
    employee = models.Employee(
        organisation_id=org.id, user_id=user.id,
        employee_identifier=user.staff_identifier, display_name='Controller',
        status='active', source_kind='legacy_user',
    )
    with aggregate_mutation(db, 'employees'):
        db.add(employee)
        db.flush()
    customer = models.Customer(name='Customer', organisation_id=org.id)
    db.add(customer)
    db.flush()
    site = models.Site(
        organisation_id=org.id, customer_id=customer.id, name='Site',
        address='1 Example Road', timezone='UTC', status='active', source_kind='native',
    )
    with aggregate_mutation(db, 'sites'):
        db.add(site)
        db.flush()
    db.commit()
    return org, user, employee, site


def command(org, user, employee, target_type, target_id, permission, **kwargs):
    return CorrectionCommand(
        target_type=target_type, target_id=target_id,
        correction_type=kwargs.pop('correction_type', 'factual_correction'),
        reason_code=kwargs.pop('reason_code', 'OPERATOR_CORRECTION'),
        explanation=kwargs.pop('explanation', 'Correct a confirmed operational error.'),
        actor_user_id=user.id, actor_employee_id=employee.id,
        organisation_id=org.id, permission=permission,
        granted_permissions=frozenset({permission}),
        correlation_id=f'test-{uuid.uuid4().hex}', **kwargs,
    )


def test_flush_boundary_blocks_active_policy_edit_and_session_recovers(db):
    org, _, _, _ = foundation(db)
    policy = models.CompanyPolicy(
        organisation_id=org.id, policy_type='staffing', version=1,
        status='active', policy_data={'minimum': 2},
    )
    with aggregate_mutation(db, 'company_policies'):
        db.add(policy)
        db.commit()
    policy.policy_data = {'minimum': 3}
    with aggregate_mutation(db, 'company_policies'):
        with pytest.raises(ImmutableRecord):
            db.flush()
    db.rollback()
    assert db.query(models.Organisation).filter_by(id=org.id).one()


def test_legal_draft_update_and_transition_remain_available(db):
    org, _, employee, _ = foundation(db)
    policy = models.CompanyPolicy(
        organisation_id=org.id, policy_type='staffing', version=1,
        status='draft', policy_data={'minimum': 1},
    )
    with aggregate_mutation(db, 'company_policies'):
        db.add(policy)
        db.flush()
        policy.policy_data = {'minimum': 2}
        policy.status = 'approved'
        policy.approved_by_employee_id = employee.id
        db.flush()
    assert policy.status == 'approved'


def test_policy_replacement_activation_is_atomic(db):
    org, user, employee, _ = foundation(db)
    current = models.CompanyPolicy(
        organisation_id=org.id, policy_type='staffing', version=1,
        status='active', policy_data={'minimum': 1},
    )
    replacement = models.CompanyPolicy(
        organisation_id=org.id, policy_type='staffing', version=2,
        status='approved', policy_data={'minimum': 2},
    )
    with aggregate_mutation(db, 'company_policies'):
        db.add_all([current, replacement])
        db.commit()
    cmd = command(org, user, employee, DomainObjectType.COMPANY_POLICY, replacement.id, 'company.manage')
    with transactional(db, owner='policy.activate'):
        activate_policy(db, policy_id=replacement.id, command=cmd)
    assert db.get(models.CompanyPolicy, current.id).status == 'superseded'
    assert db.get(models.CompanyPolicy, replacement.id).status == 'active'
    assert db.query(models.AuditLog).filter_by(action='company_policy.activated').one()


def test_post_order_active_version_is_immutable_and_replacement_preserves_acknowledgement(db):
    org, user, employee, site = foundation(db)
    order = models.PostOrder(organisation_id=org.id, site_id=site.id, title='Gate')
    with aggregate_mutation(db, 'post_orders'):
        db.add(order)
        db.flush()
        active = models.PostOrderVersion(
            organisation_id=org.id, post_order_id=order.id, version=1,
            status='active', content='Original', content_checksum='original-checksum',
        )
        db.add(active)
        db.flush()
        acknowledgement = models.PostOrderAcknowledgement(
            organisation_id=org.id, post_order_version_id=active.id,
            employee_id=employee.id,
        )
        db.add(acknowledgement)
        db.commit()
    active.content = 'Overwrite'
    with aggregate_mutation(db, 'post_orders'):
        with pytest.raises(ImmutableRecord):
            db.flush()
    db.rollback()
    with transactional(db, owner='post-order.draft'):
        replacement = create_post_order_draft(
            db, organisation_id=org.id, post_order_id=order.id,
            content='Corrected', created_by_employee_id=employee.id,
            supersedes_id=active.id,
        )
        approve_post_order_version(
            db, organisation_id=org.id, version_id=replacement.id,
            actor_employee_id=employee.id,
        )
    cmd = command(org, user, employee, DomainObjectType.POST_ORDER, order.id, 'company.manage')
    with transactional(db, owner='post-order.activate'):
        activate_post_order_version(db, version_id=replacement.id, command=cmd)
    assert db.get(models.PostOrderVersion, active.id).content == 'Original'
    assert db.get(models.PostOrderAcknowledgement, acknowledgement.id).post_order_version_id == active.id


def test_shift_assignment_and_occurrence_amendments_preserve_originals(db):
    org, user, employee, site = foundation(db)
    now = datetime.now(timezone.utc)
    shift = models.Shift(
        organisation_id=org.id, site_id=site.id, name='Completed',
        starts_at=now, ends_at=now + timedelta(hours=8), status='completed',
    )
    with aggregate_mutation(db, 'shifts'):
        db.add(shift)
        db.flush()
        assignment = models.ShiftAssignment(
            organisation_id=org.id, shift_id=shift.id,
            employee_id=employee.id, status='completed',
        )
        db.add(assignment)
        db.commit()
    shift.name = 'Overwrite'
    with aggregate_mutation(db, 'shifts'):
        with pytest.raises(ImmutableRecord):
            db.flush()
    db.rollback()
    cmd = command(org, user, employee, DomainObjectType.SHIFT, shift.id, 'patrols.manage')
    with transactional(db, owner='shift.amend'):
        amended = amend_shift(db, shift_id=shift.id, command=cmd, name='Corrected')
        corrected_assignment = amend_shift_assignment(db, assignment_id=assignment.id, command=cmd)
    assert amended.amendment_of_id == shift.id
    assert db.get(models.Shift, shift.id).name == 'Completed'
    assert db.get(models.ShiftAssignment, assignment.id).status == 'completed'
    assert corrected_assignment.id != assignment.id

    patrol = models.Patrol(
        organisation_id=org.id, name='Original Patrol', lifecycle_status='completed',
        required_officers=1, template_snapshot={'version': 1},
    )
    db.add(patrol)
    db.commit()
    patrol_cmd = command(org, user, employee, DomainObjectType.PATROL_OCCURRENCE, patrol.id, 'patrols.manage')
    with transactional(db, owner='patrol.amend'):
        amended_patrol = amend_patrol_occurrence(
            db, patrol_id=patrol.id, command=patrol_cmd, name='Corrected Patrol',
        )
    assert amended_patrol.amendment_of_id == patrol.id
    assert amended_patrol.template_snapshot == {'version': 1}
    assert db.get(models.Patrol, patrol.id).name == 'Original Patrol'


def test_template_replacement_does_not_refresh_occurrence_snapshot(db):
    org, user, employee, site = foundation(db)
    template = models.PatrolTemplate(
        organisation_id=org.id, site_id=site.id, name='Template',
        status='active', version=1, instructions='Original instruction',
    )
    with aggregate_mutation(db, 'patrol_templates'):
        db.add(template)
        db.flush()
    occurrence = models.Patrol(
        organisation_id=org.id, name='Occurrence', template_id=template.id,
        lifecycle_status='scheduled', template_snapshot={'instructions': 'Original instruction'},
    )
    db.add(occurrence)
    db.commit()
    template.instructions = 'Overwrite'
    with aggregate_mutation(db, 'patrol_templates'):
        with pytest.raises(ImmutableRecord):
            db.flush()
    db.rollback()
    cmd = command(org, user, employee, DomainObjectType.PATROL_TEMPLATE, template.id, 'patrols.manage')
    with transactional(db, owner='template.replace'):
        replacement = replace_patrol_template(
            db, template_id=template.id, command=cmd, instructions='Corrected instruction',
        )
    assert replacement.supersedes_id == template.id
    assert db.get(models.Patrol, occurrence.id).template_snapshot == {'instructions': 'Original instruction'}


def test_verification_events_and_operational_events_are_append_only_with_corrections(db):
    org, user, employee, site = foundation(db)
    checkpoint = models.Checkpoint(
        organisation_id=org.id, site_id=site.id, name='Gate', code='GATE-1', status='pending',
    )
    db.add(checkpoint)
    db.flush()
    original = models.CheckpointVerificationEvent(
        organisation_id=org.id, checkpoint_id=checkpoint.id, employee_id=employee.id,
        occurred_at=datetime.now(timezone.utc), verification_method='legacy_code',
        result='accepted', source_kind='legacy_checkpoint_state',
        event_kind='original', record_provenance='legacy_low_assurance',
    )
    with aggregate_mutation(db, 'checkpoint_verifications'):
        db.add(original)
        db.flush()
    register_domain_object(
        db, organisation_id=org.id,
        object_type=DomainObjectType.CHECKPOINT_VERIFICATION, object_id=original.id,
    )
    db.commit()
    original.result = 'rejected'
    with aggregate_mutation(db, 'checkpoint_verifications'):
        with pytest.raises(ImmutableRecord):
            db.flush()
    db.rollback()
    db.delete(original)
    with pytest.raises(HardDeleteForbidden):
        db.flush()
    db.rollback()
    cmd = command(org, user, employee, DomainObjectType.CHECKPOINT_VERIFICATION, original.id, 'checkpoints.manage')
    with transactional(db, owner='verification.correct'):
        correction = correct_checkpoint_verification(
            db, original_event_id=original.id, command=cmd, result='rejected',
        )
    assert correction.correction_of_id == original.id
    assert db.get(models.CheckpointVerificationEvent, original.id).record_provenance == 'legacy_low_assurance'

    event = db.query(models.AuditLog).filter_by(action='checkpoint_verification.corrected').one()
    event.action = 'rewritten'
    with pytest.raises(ImmutableRecord):
        db.flush()
    db.rollback()
    event_cmd = command(
        org, user, employee, DomainObjectType.CHECKPOINT_VERIFICATION, original.id,
        'checkpoints.manage', original_id=event.id,
    )
    with transactional(db, owner='event.correct'):
        corrected_event = correct_operational_event(
            db, original_event_id=event.id, command=event_cmd,
            action='checkpoint_verification.event_corrected',
        )
    assert corrected_event.correction_of_id == event.id


def test_cross_tenant_and_invalid_correction_commands_fail_closed(db):
    first, user, employee, site = foundation(db, 'first')
    second, _, _, _ = foundation(db, 'second')
    checkpoint = models.Checkpoint(
        organisation_id=first.id, site_id=site.id, name='Gate', code='CROSS', status='pending',
    )
    db.add(checkpoint)
    db.flush()
    event = models.CheckpointVerificationEvent(
        organisation_id=first.id, checkpoint_id=checkpoint.id, employee_id=employee.id,
        occurred_at=datetime.now(timezone.utc), verification_method='code', result='accepted',
        event_kind='original', record_provenance='native_confirmation',
    )
    with aggregate_mutation(db, 'checkpoint_verifications'):
        db.add(event)
        db.commit()
    wrong = CorrectionCommand(
        target_type=DomainObjectType.CHECKPOINT_VERIFICATION, target_id=event.id,
        correction_type='factual', reason_code='FIX', explanation='Wrong tenant attempt',
        actor_user_id=user.id, actor_employee_id=employee.id,
        organisation_id=second.id, permission='checkpoints.manage',
        granted_permissions=frozenset({'checkpoints.manage'}), correlation_id='cross-tenant',
    )
    with pytest.raises(CrossTenantReference):
        with transactional(db, owner='cross-tenant'):
            correct_checkpoint_verification(db, original_event_id=event.id, command=wrong, result='rejected')
    missing_reason = command(
        first, user, employee, DomainObjectType.CHECKPOINT_VERIFICATION, event.id,
        'checkpoints.manage', explanation='',
    )
    with pytest.raises(CorrectionReasonRequired):
        missing_reason.validate()
    no_permission = CorrectionCommand(
        **{**command(first, user, employee, DomainObjectType.CHECKPOINT_VERIFICATION, event.id, 'checkpoints.manage').__dict__, 'granted_permissions': frozenset()}
    )
    with pytest.raises(CorrectionPermissionRequired):
        no_permission.validate()


def test_resolved_incident_reopening_requires_controlled_command(db):
    org, user, employee, _ = foundation(db)
    incident = models.Alert(
        organisation_id=org.id, title='Resolved', severity='high', status='resolved',
        reported_at=datetime.now(timezone.utc), record_version=3,
    )
    db.add(incident)
    db.commit()
    incident.title = 'Overwrite'
    with pytest.raises(ImmutableRecord):
        db.flush()
    db.rollback()
    cmd = command(
        org, user, employee, DomainObjectType.INCIDENT, incident.id,
        'incidents.manage', expected_record_version=3, expected_state='resolved',
    )
    with transactional(db, owner='incident.reopen'):
        reopen_incident(db, incident_id=incident.id, command=cmd)
    assert db.get(models.Alert, incident.id).status == 'investigating'
    assert db.query(models.AuditLog).filter_by(action='incident.reopened').one()


def test_evidence_and_report_corrections_preserve_original_history(db):
    org, user, employee, site = foundation(db)
    evidence = models.EvidenceAttachment(
        organisation_id=org.id, storage_key='original/key', original_filename='original.jpg',
        media_type='image/jpeg', byte_size=10, content_hash='original-hash',
        status='available', retention_status='active',
    )
    with aggregate_mutation(db, 'evidence'):
        db.add(evidence)
        db.flush()
    register_domain_object(db, organisation_id=org.id, object_type=DomainObjectType.EVIDENCE, object_id=evidence.id)
    target = register_domain_object(db, organisation_id=org.id, object_type=DomainObjectType.SITE, object_id=site.id)
    with aggregate_mutation(db, 'evidence'):
        link_one = models.EvidenceLink(organisation_id=org.id, evidence_attachment_id=evidence.id, domain_object_id=target.id)
        db.add(link_one)
        db.commit()
    evidence.content_hash = 'rewritten'
    with aggregate_mutation(db, 'evidence'):
        with pytest.raises(ImmutableRecord):
            db.flush()
    db.rollback()
    cmd = command(org, user, employee, DomainObjectType.EVIDENCE, evidence.id, 'operations.write')
    with transactional(db, owner='evidence.replace'):
        replacement = replace_evidence(
            db, evidence_id=evidence.id, command=cmd, storage_key='replacement/key',
            original_filename='replacement.jpg', media_type='image/jpeg',
            byte_size=11, content_hash='replacement-hash',
        )
    assert replacement.supersedes_id == evidence.id
    assert db.get(models.EvidenceAttachment, evidence.id).content_hash == 'original-hash'
    unlink_cmd = command(org, user, employee, DomainObjectType.EVIDENCE, evidence.id, 'operations.write')
    with transactional(db, owner='evidence.unlink'):
        record_evidence_unlink(db, link_id=link_one.id, command=unlink_cmd)
    assert db.get(models.EvidenceAttachment, evidence.id)

    report = models.DailyActivityReport(
        organisation_id=org.id, site_id=site.id, report_key='daily',
        report_date=datetime.now(timezone.utc), revision=1, status='approved',
        content={'original': True}, snapshot_checksum='original-checksum',
        site_snapshot={'name': 'Site'},
    )
    with aggregate_mutation(db, 'daily_activity_reports'):
        db.add(report)
        db.flush()
    register_domain_object(
        db, organisation_id=org.id,
        object_type=DomainObjectType.DAILY_ACTIVITY_REPORT, object_id=report.id,
    )
    db.commit()
    report.content = {'rewritten': True}
    with aggregate_mutation(db, 'daily_activity_reports'):
        with pytest.raises(ImmutableRecord):
            db.flush()
    db.rollback()
    report_cmd = command(org, user, employee, DomainObjectType.DAILY_ACTIVITY_REPORT, report.id, 'reports.read')
    with transactional(db, owner='report.correct'):
        revision = correct_report(db, report_id=report.id, command=report_cmd, corrected_content={'corrected': True})
    assert revision.correction_of_id == report.id
    assert db.get(models.DailyActivityReport, report.id).snapshot_checksum == 'original-checksum'


def test_hard_delete_of_operational_history_is_forbidden(db):
    org, _, employee, site = foundation(db)
    shift = models.Shift(
        organisation_id=org.id, site_id=site.id, name='History',
        starts_at=datetime.now(timezone.utc), ends_at=datetime.now(timezone.utc),
        status='completed',
    )
    with aggregate_mutation(db, 'shifts'):
        db.add(shift)
        db.commit()
    db.delete(shift)
    with pytest.raises(HardDeleteForbidden):
        db.flush()


def test_event_failure_rolls_back_policy_supersession(db, monkeypatch):
    org, user, employee, _ = foundation(db)
    current = models.CompanyPolicy(
        organisation_id=org.id, policy_type='response', version=1,
        status='active', policy_data={'level': 1},
    )
    replacement = models.CompanyPolicy(
        organisation_id=org.id, policy_type='response', version=2,
        status='approved', policy_data={'level': 2},
    )
    with aggregate_mutation(db, 'company_policies'):
        db.add_all([current, replacement])
        db.commit()
    cmd = command(org, user, employee, DomainObjectType.COMPANY_POLICY, replacement.id, 'company.manage')
    monkeypatch.setattr(
        'backend.app.services.company_policies.emit_correction_event',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('event failure')),
    )
    with pytest.raises(PersistenceFailure):
        with transactional(db, owner='policy.failure'):
            activate_policy(db, policy_id=replacement.id, command=cmd)
    assert db.get(models.CompanyPolicy, current.id).status == 'active'
    assert db.get(models.CompanyPolicy, replacement.id).status == 'approved'


def test_registry_failure_rolls_back_template_replacement(db, monkeypatch):
    org, user, employee, site = foundation(db)
    template = models.PatrolTemplate(
        organisation_id=org.id, site_id=site.id, name='Template', status='active', version=1,
    )
    with aggregate_mutation(db, 'patrol_templates'):
        db.add(template)
        db.commit()
    cmd = command(org, user, employee, DomainObjectType.PATROL_TEMPLATE, template.id, 'patrols.manage')
    monkeypatch.setattr(
        'backend.app.services.patrol_templates.register_domain_object',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('registry failure')),
    )
    with pytest.raises(PersistenceFailure):
        with transactional(db, owner='template.failure'):
            replace_patrol_template(db, template_id=template.id, command=cmd, name='Replacement')
    assert db.query(models.PatrolTemplate).filter_by(supersedes_id=template.id).count() == 0


def test_projection_failure_rolls_back_verification_event(db, monkeypatch):
    org, user, employee, site = foundation(db)
    checkpoint = models.Checkpoint(
        organisation_id=org.id, site_id=site.id, name='Gate', code='ATOMIC', status='pending',
    )
    db.add(checkpoint)
    db.commit()
    monkeypatch.setattr(
        'backend.app.services.checkpoint_verifications.register_domain_object',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('projection failure')),
    )
    with pytest.raises(PersistenceFailure):
        with transactional(db, owner='verification.failure'):
            confirm_checkpoint(
                db, checkpoint=checkpoint, employee_id=employee.id,
                actor_user_id=user.id, occurred_at=datetime.now(timezone.utc),
                verification_method='code',
            )
    assert db.get(models.Checkpoint, checkpoint.id).status == 'pending'
    assert db.query(models.CheckpointVerificationEvent).filter_by(checkpoint_id=checkpoint.id).count() == 0
