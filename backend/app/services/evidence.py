from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .. import models
from ..domain.corrections import CorrectionCommand
from ..domain.errors import HardDeleteForbidden, ImmutableRecord
from ..domain.immutability import approved_correction
from ..domain.registry import DomainObjectType
from .corrections import emit_correction_event, validate_correction_target
from .domain_registry import require_domain_object
from .domain_registry import register_domain_object
from .tenant_validation import aggregate_mutation, require_tenant_record
from .transactions import require_transaction
from .concurrency import advance_version, lock_tenant_record
from .idempotency import execute_idempotent


def link_evidence(
    db: Session,
    *,
    organisation_id: int,
    evidence_attachment_id: int,
    domain_object_id: int,
    linked_by_employee_id: int | None,
) -> models.EvidenceLink:
    require_transaction(db)
    evidence = require_tenant_record(
        db, models.EvidenceAttachment, record_id=evidence_attachment_id,
        organisation_id=organisation_id, relationship='EvidenceLink.evidence_attachment_id',
    )
    target = require_domain_object(db, organisation_id=organisation_id, domain_object_id=domain_object_id)
    locked_target = db.query(models.DomainObject).filter(
        models.DomainObject.id == target.id,
        models.DomainObject.organisation_id == organisation_id,
        models.DomainObject.retired_at.is_(None),
    ).populate_existing().with_for_update().one_or_none()
    if locked_target is None or locked_target.retired_at is not None:
        from ..domain.errors import InvalidObjectReference
        raise InvalidObjectReference('EvidenceLink.domain_object_id', archived=True)
    target = locked_target
    if linked_by_employee_id is not None:
        require_tenant_record(
            db, models.Employee, record_id=linked_by_employee_id,
            organisation_id=organisation_id, relationship='EvidenceLink.linked_by_employee_id',
        )
    link = models.EvidenceLink(
        organisation_id=organisation_id,
        evidence_attachment_id=evidence.id,
        domain_object_id=target.id,
        linked_by_employee_id=linked_by_employee_id,
    )
    with aggregate_mutation(db, 'evidence'):
        db.add(link)
        db.flush()
    return link


def accept_evidence(
    db: Session, *, evidence_id: int, organisation_id: int,
    actor_employee_id: int, acceptance_version: int = 1,
    expected_version: int | None = None,
    idempotency_key: str | None = None,
):
    require_transaction(db)
    def execute():
        evidence = lock_tenant_record(
            db, models.EvidenceAttachment, record_id=evidence_id,
            organisation_id=organisation_id, relationship='Evidence attachment',
        )
        if evidence.status not in {'uploading', 'quarantined'}:
            raise ImmutableRecord('evidence_attachment', evidence.status)
        now = datetime.now(timezone.utc)
        with aggregate_mutation(db, 'evidence'):
            evidence.status = 'available'
            evidence.accepted_at = now
            evidence.accepted_by_employee_id = actor_employee_id
            evidence.acceptance_version = acceptance_version
            evidence.immutable_at = now
            advance_version(evidence, expected_version)
            db.flush()
        return evidence
    result = execute_idempotent(
        db, organisation_id=organisation_id, actor_user_id=None,
        actor_scope=f'employee:{actor_employee_id}', command_type='evidence.accept',
        key=idempotency_key,
        fingerprint_payload={'evidence_id': evidence_id, 'acceptance_version': acceptance_version},
        execute=execute,
        replay=lambda metadata: require_tenant_record(
            db, models.EvidenceAttachment, record_id=int(metadata['evidence_id']),
            organisation_id=organisation_id, relationship='Evidence attachment',
            allow_archived=True,
        ), result_metadata=lambda evidence: {
            'evidence_id': evidence.id, 'status': evidence.status,
            'record_version': evidence.record_version,
        },
    )
    return result.value


def replace_evidence(
    db: Session, *, evidence_id: int, command: CorrectionCommand,
    storage_key: str, original_filename: str, media_type: str,
    byte_size: int, content_hash: str,
):
    original = require_tenant_record(
        db, models.EvidenceAttachment, record_id=evidence_id,
        organisation_id=command.organisation_id, relationship='Evidence attachment',
        allow_archived=True,
    )
    validate_correction_target(db, command=command, record=original, object_type=DomainObjectType.EVIDENCE)
    if original.status != 'available':
        raise ImmutableRecord('evidence_attachment', original.status)
    replacement = models.EvidenceAttachment(
        organisation_id=command.organisation_id, storage_key=storage_key,
        original_filename=original_filename, media_type=media_type,
        byte_size=byte_size, content_hash=content_hash, status='pending',
        retention_status=original.retention_status,
        created_by_employee_id=command.actor_employee_id,
        supersedes_id=original.id, correction_of_id=original.id,
    )
    with aggregate_mutation(db, 'evidence'):
        db.add(replacement)
        db.flush()
        with approved_correction(db, original, command):
            original.status = 'superseded'
            original.record_version += 1
            db.flush()
    register_domain_object(
        db, organisation_id=command.organisation_id,
        object_type=DomainObjectType.EVIDENCE, object_id=replacement.id,
    )
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.EVIDENCE,
        record=original, action='evidence.replaced',
        additional_metadata={'replacement_id': replacement.id},
    )
    return replacement


def record_evidence_unlink(
    db: Session, *, link_id: int, command: CorrectionCommand,
):
    """Retain the historical link and append its controlled removal fact."""
    link = require_tenant_record(
        db, models.EvidenceLink, record_id=link_id,
        organisation_id=command.organisation_id, relationship='Evidence link',
        allow_archived=True,
    )
    attachment = require_tenant_record(
        db, models.EvidenceAttachment, record_id=link.evidence_attachment_id,
        organisation_id=command.organisation_id, relationship='Evidence attachment',
        allow_archived=True,
    )
    validate_correction_target(db, command=command, record=attachment, object_type=DomainObjectType.EVIDENCE)
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.EVIDENCE,
        record=attachment, action='evidence.link_removed',
        additional_metadata={'link_id': link.id, 'domain_object_id': link.domain_object_id},
    )
    return attachment


def hard_delete_evidence(*_args, **_kwargs):
    raise HardDeleteForbidden()
