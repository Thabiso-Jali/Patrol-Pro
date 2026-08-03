from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .. import models
from ..domain.errors import DomainError, DomainErrorCode, RegistryIntegrityError
from ..domain.registry import DOMAIN_OBJECT_OWNERS, DomainObjectType, canonical_aggregate_root_id
from ..domain.corrections import CorrectionCommand
from .tenant_validation import aggregate_mutation, require_tenant_record, validate_tenant_relationships
from .transactions import require_transaction


DOMAIN_OBJECT_MODELS = {
    DomainObjectType.ORGANISATION: models.Organisation,
    DomainObjectType.CUSTOMER: models.Customer,
    DomainObjectType.SITE: models.Site,
    DomainObjectType.CONTACT: models.Contact,
    DomainObjectType.EMPLOYEE: models.Employee,
    DomainObjectType.TEAM: models.Team,
    DomainObjectType.SHIFT: models.Shift,
    DomainObjectType.PATROL_TEMPLATE: models.PatrolTemplate,
    DomainObjectType.PATROL_OCCURRENCE: models.Patrol,
    DomainObjectType.CHECKPOINT: models.Checkpoint,
    DomainObjectType.CHECKPOINT_VERIFICATION: models.CheckpointVerificationEvent,
    DomainObjectType.INCIDENT: models.Alert,
    DomainObjectType.OPERATIONAL_ALERT: models.OperationalAlert,
    DomainObjectType.NOTIFICATION: models.Notification,
    DomainObjectType.EVIDENCE: models.EvidenceAttachment,
    DomainObjectType.DAILY_ACTIVITY_REPORT: models.DailyActivityReport,
    DomainObjectType.POST_ORDER: models.PostOrder,
    DomainObjectType.SITE_ASSET: models.SiteAsset,
    DomainObjectType.COMPANY_POLICY: models.CompanyPolicy,
}


def _require_source_object(
    db: Session, *, organisation_id: int, object_type: DomainObjectType, object_id: int
):
    model = DOMAIN_OBJECT_MODELS[object_type]
    try:
        source = require_tenant_record(
            db, model, record_id=object_id, organisation_id=organisation_id,
            relationship='DomainObject.object_id',
        )
    except DomainError as exc:
        if getattr(exc, 'code', None) in {
            DomainErrorCode.MISSING_REQUIRED_RELATIONSHIP,
            DomainErrorCode.CROSS_TENANT_REFERENCE,
        }:
            raise RegistryIntegrityError(
                DomainErrorCode.ORPHANED_DOMAIN_OBJECT,
                'A domain object cannot be registered without its source record.',
            ) from exc
        raise
    validate_tenant_relationships(db, source, validate_all=True)
    if getattr(source, 'is_deleted', False) or getattr(source, 'retired_at', None) is not None:
        raise RegistryIntegrityError(
            DomainErrorCode.DELETED_OBJECT_REFERENCE,
            'Deleted or retired records cannot be registered.',
        )
    if getattr(source, 'status', None) in {'archived', 'retired'}:
        raise RegistryIntegrityError(
            DomainErrorCode.ARCHIVED_OBJECT_REFERENCE,
            'Archived records cannot be registered.',
        )
    return source


def register_domain_object(
    db: Session,
    *,
    organisation_id: int,
    object_type: DomainObjectType,
    object_id: int,
    aggregate_root_id: int | None = None,
) -> models.DomainObject:
    object_type = DomainObjectType(object_type)
    root_type, service = DOMAIN_OBJECT_OWNERS[object_type]
    source = _require_source_object(
        db, organisation_id=organisation_id, object_type=object_type, object_id=object_id,
    )
    canonical_root_id = canonical_aggregate_root_id(object_type, source)
    if aggregate_root_id is not None and aggregate_root_id != canonical_root_id:
        raise RegistryIntegrityError(
            DomainErrorCode.AGGREGATE_OWNERSHIP_VIOLATION,
            'Caller-supplied aggregate ownership does not match the source record.',
        )
    existing = db.query(models.DomainObject).filter(
        models.DomainObject.object_type == object_type.value,
        models.DomainObject.object_id == object_id,
    ).first()
    if existing:
        if existing.organisation_id != organisation_id:
            raise RegistryIntegrityError(
                DomainErrorCode.DUPLICATE_DOMAIN_REGISTRATION,
                'This source record is already registered to another organisation.',
            )
        if existing.retired_at is not None:
            raise RegistryIntegrityError(
                DomainErrorCode.ARCHIVED_OBJECT_REFERENCE,
                'A retired domain registration cannot be reused.',
            )
        return existing
    registered = models.DomainObject(
        organisation_id=organisation_id,
        object_type=object_type.value,
        object_id=object_id,
        aggregate_root_type=root_type,
        aggregate_root_id=canonical_root_id,
        owning_service=service,
    )
    with aggregate_mutation(db, 'domain_registry'):
        db.add(registered)
        db.flush()
    return registered


def require_domain_object(
    db: Session, *, organisation_id: int, domain_object_id: int
) -> models.DomainObject:
    registered = db.query(models.DomainObject).filter(
        models.DomainObject.id == domain_object_id,
        models.DomainObject.organisation_id == organisation_id,
        models.DomainObject.retired_at.is_(None),
    ).populate_existing().with_for_update().first()
    if not registered:
        raise RegistryIntegrityError(
            DomainErrorCode.DOMAIN_OBJECT_NOT_REGISTERED,
            'Domain object does not exist in this organisation.',
        )
    _require_source_object(
        db,
        organisation_id=organisation_id,
        object_type=DomainObjectType(registered.object_type),
        object_id=registered.object_id,
    )
    return registered


def retire_domain_object(
    db: Session, *, organisation_id: int, domain_object_id: int,
    command: CorrectionCommand,
) -> models.DomainObject:
    require_transaction(db)
    command.validate()
    registered = db.query(models.DomainObject).filter(
        models.DomainObject.id == domain_object_id,
        models.DomainObject.organisation_id == organisation_id,
        models.DomainObject.retired_at.is_(None),
    ).populate_existing().with_for_update().first()
    if registered is None:
        raise RegistryIntegrityError(
            DomainErrorCode.DOMAIN_OBJECT_NOT_REGISTERED,
            'Domain object does not exist in this organisation.',
        )
    if (
        command.organisation_id != organisation_id
        or DomainObjectType(command.target_type).value != registered.object_type
        or command.target_id != registered.object_id
    ):
        raise RegistryIntegrityError(
            DomainErrorCode.DOMAIN_OBJECT_NOT_REGISTERED,
            'Domain object does not exist in this organisation.',
        )
    link_exists = any(
        db.query(model.id).filter(
            model.organisation_id == organisation_id,
            model.domain_object_id == domain_object_id,
        ).first()
        for model in (
            models.EvidenceLink, models.Notification, models.AuditLog,
            models.OperationalEventSubject, models.OperationalAlert,
        )
    )
    if link_exists:
        raise RegistryIntegrityError(
            DomainErrorCode.MISSING_REQUIRED_RELATIONSHIP,
            'A referenced domain object cannot be retired.',
        )
    from .operational_events import append_operational_event
    append_operational_event(
        db, organisation_id=organisation_id, action='domain_object.retired',
        actor_user_id=command.actor_user_id,
        actor_employee_id=command.actor_employee_id,
        domain_object_id=registered.id,
        event_metadata=command.event_metadata(),
        correlation_id=command.correlation_id,
    )
    with aggregate_mutation(db, 'domain_registry'):
        registered.retired_at = datetime.now(timezone.utc)
        db.flush()
    return registered
