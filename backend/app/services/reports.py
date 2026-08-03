import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .. import models
from ..domain.corrections import CorrectionCommand
from ..domain.errors import ImmutableRecord
from ..domain.immutability import approved_correction
from ..domain.registry import DomainObjectType
from .corrections import emit_correction_event, validate_correction_target
from .domain_registry import register_domain_object
from .tenant_validation import aggregate_mutation, require_tenant_record
from .transactions import require_transaction
from .concurrency import advance_version, lock_tenant_record
from .idempotency import execute_idempotent


def _checksum(content: dict) -> str:
    encoded = json.dumps(content, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def generate_report(db: Session, *, report_id: int, organisation_id: int, site_snapshot: dict,
                    expected_version: int | None = None):
    require_transaction(db)
    report = lock_tenant_record(
        db, models.DailyActivityReport, record_id=report_id,
        organisation_id=organisation_id, relationship='Daily Activity Report',
    )
    if report.status != 'draft':
        raise ImmutableRecord('daily_activity_report', report.status)
    with aggregate_mutation(db, 'daily_activity_reports'):
        report.snapshot_checksum = _checksum(report.content)
        report.site_snapshot = site_snapshot
        report.generated_at = datetime.now(timezone.utc)
        report.status = 'generated'
        advance_version(report, expected_version)
        db.flush()
    return report


def _approve_report(db: Session, *, report_id: int, command: CorrectionCommand):
    report = lock_tenant_record(
        db, models.DailyActivityReport, record_id=report_id,
        organisation_id=command.organisation_id, relationship='Daily Activity Report',
    )
    validate_correction_target(db, command=command, record=report, object_type=DomainObjectType.DAILY_ACTIVITY_REPORT)
    if report.status != 'generated':
        raise ImmutableRecord('daily_activity_report', report.status)
    with aggregate_mutation(db, 'daily_activity_reports'):
        with approved_correction(db, report, command):
            report.status = 'approved'
            report.approved_by_employee_id = command.actor_employee_id
            report.approved_at = datetime.now(timezone.utc)
            report.approval_version = report.record_version
            advance_version(report, command.expected_record_version, required=True)
            db.flush()
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.DAILY_ACTIVITY_REPORT,
        record=report, action='daily_activity_report.approved',
    )
    return report


def approve_report(
    db: Session, *, report_id: int, command: CorrectionCommand,
    idempotency_key: str | None = None,
):
    result = execute_idempotent(
        db, organisation_id=command.organisation_id,
        actor_user_id=command.actor_user_id, actor_scope=(
            f'employee:{command.actor_employee_id}' if command.actor_user_id is None else None
        ), command_type='daily_report.approve', key=idempotency_key,
        fingerprint_payload={
            'report_id': report_id, 'expected_version': command.expected_record_version,
            'reason_code': command.reason_code,
        }, execute=lambda: _approve_report(db, report_id=report_id, command=command),
        replay=lambda metadata: require_tenant_record(
            db, models.DailyActivityReport, record_id=int(metadata['report_id']),
            organisation_id=command.organisation_id, relationship='Daily Activity Report',
            allow_archived=True,
        ), result_metadata=lambda report: {
            'report_id': report.id, 'status': report.status,
            'record_version': report.record_version,
        },
    )
    return result.value


def correct_report(db: Session, *, report_id: int, command: CorrectionCommand, corrected_content: dict):
    original = require_tenant_record(
        db, models.DailyActivityReport, record_id=report_id,
        organisation_id=command.organisation_id, relationship='Daily Activity Report',
        allow_archived=True,
    )
    validate_correction_target(db, command=command, record=original, object_type=DomainObjectType.DAILY_ACTIVITY_REPORT)
    if original.status not in {'generated', 'approved', 'delivered', 'superseded'}:
        raise ImmutableRecord('daily_activity_report', original.status)
    revision = models.DailyActivityReport(
        organisation_id=command.organisation_id, site_id=original.site_id,
        report_key=original.report_key, report_date=original.report_date,
        revision=original.revision + 1, status='draft', content=corrected_content,
        supersedes_id=original.id, correction_of_id=original.id,
        created_by_employee_id=command.actor_employee_id,
    )
    with aggregate_mutation(db, 'daily_activity_reports'):
        db.add(revision)
        db.flush()
    register_domain_object(
        db, organisation_id=command.organisation_id,
        object_type=DomainObjectType.DAILY_ACTIVITY_REPORT, object_id=revision.id,
    )
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.DAILY_ACTIVITY_REPORT,
        record=original, action='daily_activity_report.correction_created',
        additional_metadata={'revision_id': revision.id},
    )
    return revision
