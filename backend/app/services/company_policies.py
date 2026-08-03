from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .. import models
from ..domain.corrections import CorrectionCommand
from ..domain.errors import ActiveVersionConflict, ImmutableRecord, InvalidStateTransition
from ..domain.immutability import approved_correction
from ..domain.registry import DomainObjectType
from ..domain.states import assert_transition
from .corrections import emit_correction_event, validate_correction_target
from .tenant_validation import aggregate_mutation, require_tenant_record
from .transactions import require_transaction
from .concurrency import advance_version, assert_expected_version, lock_tenant_record
from .idempotency import execute_idempotent


def create_policy_draft(
    db: Session, *, organisation_id: int, policy_type: str, policy_data: dict,
    actor_employee_id: int | None = None, supersedes_id: int | None = None,
) -> models.CompanyPolicy:
    require_transaction(db)
    if supersedes_id is not None:
        require_tenant_record(
            db, models.CompanyPolicy, record_id=supersedes_id,
            organisation_id=organisation_id, relationship='Company Policy replacement',
            allow_archived=True,
        )
    version = (db.query(models.CompanyPolicy.version).filter(
        models.CompanyPolicy.organisation_id == organisation_id,
        models.CompanyPolicy.policy_type == policy_type,
    ).order_by(models.CompanyPolicy.version.desc()).scalar() or 0) + 1
    draft = models.CompanyPolicy(
        organisation_id=organisation_id, policy_type=policy_type, version=version,
        status='draft', policy_data=policy_data, supersedes_id=supersedes_id,
        created_by=actor_employee_id, updated_by=actor_employee_id,
    )
    with aggregate_mutation(db, 'company_policies'):
        db.add(draft)
        db.flush()
    return draft


def edit_policy_draft(db: Session, *, organisation_id: int, policy_id: int, policy_data: dict,
                      expected_version: int | None = None):
    require_transaction(db)
    policy = lock_tenant_record(
        db, models.CompanyPolicy, record_id=policy_id, organisation_id=organisation_id,
        relationship='Company Policy',
    )
    if policy.status != 'draft':
        raise ImmutableRecord('company_policy', policy.status)
    with aggregate_mutation(db, 'company_policies'):
        policy.policy_data = policy_data
        advance_version(policy, expected_version)
        db.flush()
    return policy


def approve_policy(db: Session, *, organisation_id: int, policy_id: int, actor_employee_id: int,
                   expected_version: int | None = None):
    require_transaction(db)
    policy = lock_tenant_record(db, models.CompanyPolicy, record_id=policy_id, organisation_id=organisation_id)
    assert_transition('company_policy', policy.status, 'approved')
    with aggregate_mutation(db, 'company_policies'):
        policy.status = 'approved'
        policy.approved_by_employee_id = actor_employee_id
        policy.approved_at = datetime.now(timezone.utc)
        advance_version(policy, expected_version)
        db.flush()
    return policy


def _activate_policy(db: Session, *, policy_id: int, command: CorrectionCommand):
    candidate = require_tenant_record(
        db, models.CompanyPolicy, record_id=policy_id,
        organisation_id=command.organisation_id, relationship='Company Policy',
    )
    observed_active_id = db.query(models.CompanyPolicy.id).filter(
        models.CompanyPolicy.organisation_id == command.organisation_id,
        models.CompanyPolicy.policy_type == candidate.policy_type,
        models.CompanyPolicy.status == 'active',
        models.CompanyPolicy.id != policy_id,
    ).scalar()
    versions = db.query(models.CompanyPolicy).filter(
        models.CompanyPolicy.organisation_id == command.organisation_id,
        models.CompanyPolicy.policy_type == candidate.policy_type,
    ).order_by(models.CompanyPolicy.id).with_for_update().all()
    policy = next(row for row in versions if row.id == policy_id)
    validate_correction_target(
        db, command=command, record=policy, object_type=DomainObjectType.COMPANY_POLICY,
    )
    assert_expected_version(policy, command.expected_record_version)
    if policy.status != 'approved':
        raise InvalidStateTransition('company_policy', policy.status, 'active')
    if policy.effective_from and policy.effective_from > datetime.now(timezone.utc):
        raise InvalidStateTransition('company_policy', policy.status, 'active')
    current = next((row for row in versions if row.status == 'active' and row.id != policy.id), None)
    if observed_active_id != (current.id if current else None):
        raise ActiveVersionConflict()
    with aggregate_mutation(db, 'company_policies'):
        if current:
            with approved_correction(db, current, command):
                current.status = 'superseded'
                advance_version(current)
                db.flush()
            policy.supersedes_id = current.id
        policy.status = 'active'
        advance_version(policy, command.expected_record_version)
        db.flush()
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.COMPANY_POLICY,
        record=policy, action='company_policy.activated',
        additional_metadata={'superseded_id': current.id if current else None},
    )
    return policy


def activate_policy(
    db: Session, *, policy_id: int, command: CorrectionCommand,
    idempotency_key: str | None = None,
):
    result = execute_idempotent(
        db, organisation_id=command.organisation_id,
        actor_user_id=command.actor_user_id, actor_scope=(
            f'employee:{command.actor_employee_id}' if command.actor_user_id is None
            else None
        ), command_type='company_policy.activate', key=idempotency_key,
        fingerprint_payload={
            'policy_id': policy_id, 'expected_version': command.expected_record_version,
            'reason_code': command.reason_code,
        }, execute=lambda: _activate_policy(db, policy_id=policy_id, command=command),
        replay=lambda metadata: require_tenant_record(
            db, models.CompanyPolicy, record_id=int(metadata['policy_id']),
            organisation_id=command.organisation_id, relationship='Company Policy',
            allow_archived=True,
        ), result_metadata=lambda policy: {
            'policy_id': policy.id, 'status': policy.status,
            'record_version': policy.record_version,
        },
    )
    return result.value
