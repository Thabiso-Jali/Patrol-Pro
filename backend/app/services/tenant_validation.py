from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from ..domain.errors import (
    AggregateOwnershipViolation,
    CrossTenantReference,
    InvalidObjectReference,
    DomainErrorCode,
    RegistryIntegrityError,
)


_SERVICE_STACK_KEY = 'patrol_pro_aggregate_service_stack'


@contextmanager
def aggregate_mutation(db: Session, service: str) -> Iterator[None]:
    """Declare the sole service authorised to mutate an aggregate in this scope."""
    stack = db.info.setdefault(_SERVICE_STACK_KEY, [])
    stack.append(service)
    try:
        yield
    finally:
        stack.pop()
        if not stack:
            db.info.pop(_SERVICE_STACK_KEY, None)


def assert_aggregate_owner(model_or_instance, service: str) -> None:
    expected = getattr(model_or_instance, '__owning_service__', None)
    if expected and expected != service:
        name = model_or_instance.__name__ if isinstance(model_or_instance, type) else type(model_or_instance).__name__
        raise AggregateOwnershipViolation(name, expected)


def _active_service(db: Session) -> str | None:
    stack = db.info.get(_SERVICE_STACK_KEY, ())
    return stack[-1] if stack else None


def _is_changed(instance, column_key: str) -> bool:
    state = inspect(instance)
    return instance in state.session.new or state.attrs[column_key].history.has_changes()


def _tenant_model_for_table(table_name: str):
    from .. import models

    for mapper in models.Base.registry.mappers:
        model = mapper.class_
        if model.__table__.name == table_name:
            return model
    return None


def _target_in_session(db: Session, target_model, target_id: int):
    for candidate in db.new:
        if isinstance(candidate, target_model) and candidate.id == target_id:
            return candidate
    return None


def _validate_organisation(db: Session, organisation_id: int) -> None:
    from .. import models

    organisation = db.query(models.Organisation).filter(
        models.Organisation.id == organisation_id,
    ).first()
    if not organisation:
        raise InvalidObjectReference('Organisation')
    if not organisation.is_active or organisation.status in {'archived', 'suspended'}:
        raise InvalidObjectReference('Organisation', archived=True)


def require_tenant_record(
    db: Session,
    model,
    *,
    record_id: int,
    organisation_id: int,
    relationship: str | None = None,
    allow_archived: bool = False,
):
    """Resolve an untrusted identifier without ever dropping the tenant predicate."""
    label = relationship or model.__name__
    tenant_column = model.id if model.__table__.name == 'organisations' else model.organisation_id
    record = db.query(model).filter(
        model.id == record_id,
        tenant_column == organisation_id,
    ).first()
    if record is None:
        raise CrossTenantReference(label)
    if getattr(record, 'is_deleted', False):
        raise InvalidObjectReference(label, deleted=True)
    archived = (
        getattr(record, 'retired_at', None) is not None
        or getattr(record, 'status', None) in {'archived', 'retired'}
    )
    if archived and not allow_archived:
        raise InvalidObjectReference(label, archived=True)
    return record


def _validate_reference(
    db: Session,
    *,
    instance,
    organisation_id: int,
    column,
    target_model,
    target_id: int,
) -> None:
    relationship = f'{type(instance).__name__}.{column.key}'
    target = _target_in_session(db, target_model, target_id)
    if target is None:
        require_tenant_record(
            db, target_model, record_id=target_id,
            organisation_id=organisation_id, relationship=relationship,
        )
        return
    target_organisation_id = target.id if target_model.__table__.name == 'organisations' else target.organisation_id
    if target_organisation_id != organisation_id:
        raise CrossTenantReference(relationship)
    if getattr(target, 'is_deleted', False):
        raise InvalidObjectReference(relationship, deleted=True)
    if (
        getattr(target, 'retired_at', None) is not None
        or getattr(target, 'status', None) in {'archived', 'retired'}
    ):
        raise InvalidObjectReference(relationship, archived=True)


def validate_tenant_relationships(db: Session, instance, *, validate_all: bool = False) -> None:
    """Validate every persisted foreign-key edge from one canonical mechanism."""
    organisation_id = getattr(instance, 'organisation_id', None)
    if organisation_id is None:
        return
    _validate_organisation(db, organisation_id)

    mapper = inspect(type(instance))
    for column in mapper.columns:
        if column.key == 'organisation_id' or not column.foreign_keys:
            continue
        target_id = getattr(instance, column.key)
        if target_id is None or (not validate_all and not _is_changed(instance, column.key)):
            continue
        foreign_key = next(iter(column.foreign_keys))
        target_model = _tenant_model_for_table(foreign_key.column.table.name)
        if target_model is None:
            continue
        _validate_reference(
            db,
            instance=instance,
            organisation_id=organisation_id,
            column=column,
            target_model=target_model,
            target_id=target_id,
        )


def _validate_domain_registration(db: Session, registered) -> None:
    from .. import models
    from ..domain.registry import DOMAIN_OBJECT_OWNERS, DomainObjectType, canonical_aggregate_root_id
    from .domain_registry import DOMAIN_OBJECT_MODELS

    try:
        object_type = DomainObjectType(registered.object_type)
    except ValueError as exc:
        raise RegistryIntegrityError(
            DomainErrorCode.DOMAIN_OBJECT_NOT_REGISTERED,
            'Unknown domain object types cannot be registered.',
        ) from exc
    root_type, owning_service = DOMAIN_OBJECT_OWNERS[object_type]
    if registered.aggregate_root_type != root_type or registered.owning_service != owning_service:
        raise RegistryIntegrityError(
            DomainErrorCode.AGGREGATE_OWNERSHIP_VIOLATION,
            'Domain registry ownership metadata does not match the canonical registry.',
        )
    try:
        source = require_tenant_record(
            db, DOMAIN_OBJECT_MODELS[object_type], record_id=registered.object_id,
            organisation_id=registered.organisation_id,
            relationship='DomainObject.object_id',
        )
    except CrossTenantReference as exc:
        raise RegistryIntegrityError(
            DomainErrorCode.ORPHANED_DOMAIN_OBJECT,
            'A domain registration must reference a source in the same organisation.',
        ) from exc
    if registered.aggregate_root_id != canonical_aggregate_root_id(object_type, source):
        raise RegistryIntegrityError(
            DomainErrorCode.AGGREGATE_OWNERSHIP_VIOLATION,
            'Domain registry aggregate ownership does not match the source record.',
        )
    duplicate = db.query(models.DomainObject).filter(
        models.DomainObject.object_type == object_type.value,
        models.DomainObject.object_id == registered.object_id,
        models.DomainObject.id != registered.id,
    ).first()
    if duplicate is not None:
        raise RegistryIntegrityError(
            DomainErrorCode.DUPLICATE_DOMAIN_REGISTRATION,
            'A source record can have only one domain registration.',
        )


def enforce_tenant_and_aggregate_boundaries(db: Session, _flush_context, _instances) -> None:
    """Session-level safety net; endpoints cannot bypass tenant or service ownership."""
    from ..domain.immutability import enforce_immutability

    enforce_immutability(db)
    for instance in db.deleted:
        if getattr(instance, '__owning_service__', None):
            raise InvalidObjectReference(type(instance).__name__, deleted=True)

    for instance in tuple(db.new) + tuple(db.dirty):
        expected_service = getattr(instance, '__owning_service__', None)
        if expected_service:
            active_service = _active_service(db)
            if active_service != expected_service:
                raise AggregateOwnershipViolation(type(instance).__name__, expected_service)
        validate_tenant_relationships(db, instance)
        if type(instance).__name__ == 'DomainObject':
            _validate_domain_registration(db, instance)


def prevent_bulk_tenant_mutation(execute_state) -> None:
    """Bulk ORM DML bypasses per-record ownership hooks and is therefore forbidden."""
    if execute_state.is_update or execute_state.is_delete:
        raise AggregateOwnershipViolation('Bulk tenant records', 'owning aggregate')
