import hashlib
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


def create_post_order_draft(
    db: Session, *, organisation_id: int, post_order_id: int, content: str,
    created_by_employee_id: int | None, supersedes_id: int | None = None,
):
    require_transaction(db)
    require_tenant_record(db, models.PostOrder, record_id=post_order_id, organisation_id=organisation_id)
    if supersedes_id:
        require_tenant_record(
            db, models.PostOrderVersion, record_id=supersedes_id,
            organisation_id=organisation_id, allow_archived=True,
        )
    version = (db.query(models.PostOrderVersion.version).filter(
        models.PostOrderVersion.organisation_id == organisation_id,
        models.PostOrderVersion.post_order_id == post_order_id,
    ).order_by(models.PostOrderVersion.version.desc()).scalar() or 0) + 1
    draft = models.PostOrderVersion(
        organisation_id=organisation_id, post_order_id=post_order_id,
        version=version, status='draft', content=content,
        supersedes_id=supersedes_id, created_by_employee_id=created_by_employee_id,
    )
    with aggregate_mutation(db, 'post_orders'):
        db.add(draft)
        db.flush()
    return draft


def edit_post_order_draft(db: Session, *, organisation_id: int, version_id: int, content: str,
                          expected_version: int | None = None):
    require_transaction(db)
    version = lock_tenant_record(
        db, models.PostOrderVersion, record_id=version_id,
        organisation_id=organisation_id, relationship='Post Order version',
    )
    if version.status != 'draft':
        raise ImmutableRecord('post_order_version', version.status)
    with aggregate_mutation(db, 'post_orders'):
        version.content = content
        advance_version(version, expected_version)
        db.flush()
    return version


def approve_post_order_version(db: Session, *, organisation_id: int, version_id: int,
                               actor_employee_id: int, expected_version: int | None = None):
    require_transaction(db)
    version = lock_tenant_record(
        db, models.PostOrderVersion, record_id=version_id,
        organisation_id=organisation_id, relationship='Post Order version',
    )
    assert_transition('post_order_version', version.status, 'approved')
    with aggregate_mutation(db, 'post_orders'):
        version.status = 'approved'
        version.approved_by_employee_id = actor_employee_id
        version.approved_at = datetime.now(timezone.utc)
        advance_version(version, expected_version)
        db.flush()
    return version


def _activate_post_order_version(db: Session, *, version_id: int, command: CorrectionCommand):
    candidate = require_tenant_record(
        db, models.PostOrderVersion, record_id=version_id,
        organisation_id=command.organisation_id, relationship='Post Order version',
    )
    observed_active_id = db.query(models.PostOrderVersion.id).filter(
        models.PostOrderVersion.organisation_id == command.organisation_id,
        models.PostOrderVersion.post_order_id == candidate.post_order_id,
        models.PostOrderVersion.status == 'active',
        models.PostOrderVersion.id != version_id,
    ).scalar()
    post_order = lock_tenant_record(
        db, models.PostOrder, record_id=candidate.post_order_id,
        organisation_id=command.organisation_id, relationship='Post Order',
    )
    versions = db.query(models.PostOrderVersion).filter(
        models.PostOrderVersion.organisation_id == command.organisation_id,
        models.PostOrderVersion.post_order_id == post_order.id,
    ).order_by(models.PostOrderVersion.id).with_for_update().all()
    version = next(row for row in versions if row.id == version_id)
    validate_correction_target(db, command=command, record=post_order, object_type=DomainObjectType.POST_ORDER)
    assert_expected_version(version, command.expected_record_version)
    if version.status != 'approved':
        raise InvalidStateTransition('post_order_version', version.status, 'active')
    if version.effective_from and version.effective_from > datetime.now(timezone.utc):
        raise InvalidStateTransition('post_order_version', version.status, 'active')
    current = next((row for row in versions if row.status == 'active' and row.id != version.id), None)
    if observed_active_id != (current.id if current else None):
        raise ActiveVersionConflict()
    checksum = hashlib.sha256(version.content.encode('utf-8')).hexdigest()
    with aggregate_mutation(db, 'post_orders'):
        if current:
            with approved_correction(db, current, command):
                current.status = 'superseded'
                advance_version(current)
                db.flush()
            version.supersedes_id = current.id
        version.content_checksum = checksum
        version.status = 'active'
        advance_version(version, command.expected_record_version)
        db.flush()
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.POST_ORDER,
        record=post_order, action='post_order.version_activated',
        additional_metadata={'version_id': version.id, 'superseded_id': current.id if current else None},
    )
    return version


def activate_post_order_version(
    db: Session, *, version_id: int, command: CorrectionCommand,
    idempotency_key: str | None = None,
):
    result = execute_idempotent(
        db, organisation_id=command.organisation_id,
        actor_user_id=command.actor_user_id, actor_scope=(
            f'employee:{command.actor_employee_id}' if command.actor_user_id is None else None
        ), command_type='post_order.activate', key=idempotency_key,
        fingerprint_payload={
            'version_id': version_id, 'expected_version': command.expected_record_version,
            'reason_code': command.reason_code,
        }, execute=lambda: _activate_post_order_version(db, version_id=version_id, command=command),
        replay=lambda metadata: require_tenant_record(
            db, models.PostOrderVersion, record_id=int(metadata['version_id']),
            organisation_id=command.organisation_id, relationship='Post Order version',
            allow_archived=True,
        ), result_metadata=lambda version: {
            'version_id': version.id, 'status': version.status,
            'record_version': version.record_version,
        },
    )
    return result.value
