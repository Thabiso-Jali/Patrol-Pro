from enum import StrEnum
from typing import Any


class DomainErrorCode(StrEnum):
    INVALID_STATE_TRANSITION = 'INVALID_STATE_TRANSITION'
    CROSS_TENANT_REFERENCE = 'CROSS_TENANT_REFERENCE'
    IMMUTABLE_RECORD = 'IMMUTABLE_RECORD'
    ARCHIVED_DEPENDENCY = 'ARCHIVED_DEPENDENCY'
    CONCURRENT_MODIFICATION = 'CONCURRENT_MODIFICATION'
    DUPLICATE_ASSIGNMENT = 'DUPLICATE_ASSIGNMENT'
    IDEMPOTENT_REPLAY = 'IDEMPOTENT_REPLAY'
    IDEMPOTENCY_KEY_REUSED = 'IDEMPOTENCY_KEY_REUSED'
    MISSING_REQUIRED_RELATIONSHIP = 'MISSING_REQUIRED_RELATIONSHIP'
    DOMAIN_OBJECT_NOT_REGISTERED = 'DOMAIN_OBJECT_NOT_REGISTERED'
    UNSUPPORTED_COMPATIBILITY_WRITE = 'UNSUPPORTED_COMPATIBILITY_WRITE'
    UNSAFE_MIGRATION_DOWNGRADE = 'UNSAFE_MIGRATION_DOWNGRADE'
    AGGREGATE_OWNERSHIP_VIOLATION = 'AGGREGATE_OWNERSHIP_VIOLATION'
    ARCHIVED_OBJECT_REFERENCE = 'ARCHIVED_OBJECT_REFERENCE'
    DELETED_OBJECT_REFERENCE = 'DELETED_OBJECT_REFERENCE'
    DUPLICATE_DOMAIN_REGISTRATION = 'DUPLICATE_DOMAIN_REGISTRATION'
    ORPHANED_DOMAIN_OBJECT = 'ORPHANED_DOMAIN_OBJECT'
    TRANSACTION_OWNERSHIP_VIOLATION = 'TRANSACTION_OWNERSHIP_VIOLATION'
    PERSISTENCE_FAILURE = 'PERSISTENCE_FAILURE'
    CORRECTION_REASON_REQUIRED = 'CORRECTION_REASON_REQUIRED'
    CORRECTION_PERMISSION_REQUIRED = 'CORRECTION_PERMISSION_REQUIRED'
    INVALID_CORRECTION_TARGET = 'INVALID_CORRECTION_TARGET'
    CORRECTION_CYCLE = 'CORRECTION_CYCLE'
    SUPERSEDED_RECORD = 'SUPERSEDED_RECORD'
    HARD_DELETE_FORBIDDEN = 'HARD_DELETE_FORBIDDEN'
    EXPECTED_VERSION_REQUIRED = 'EXPECTED_VERSION_REQUIRED'
    INVALID_EXPECTED_VERSION = 'INVALID_EXPECTED_VERSION'
    IDEMPOTENCY_IN_PROGRESS = 'IDEMPOTENCY_IN_PROGRESS'
    DUPLICATE_VERIFICATION = 'DUPLICATE_VERIFICATION'
    ACTIVE_VERSION_CONFLICT = 'ACTIVE_VERSION_CONFLICT'
    ARCHIVE_CONFLICT = 'ARCHIVE_CONFLICT'


class DomainError(Exception):
    """Safe, stable business error returned by canonical domain services."""

    def __init__(
        self,
        code: DomainErrorCode,
        message: str,
        *,
        status_code: int = 409,
        field_errors: list[dict[str, str]] | None = None,
        retryable: bool = False,
        current_version: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field_errors = field_errors or []
        self.retryable = retryable
        self.current_version = current_version

    def envelope(self, correlation_id: str) -> dict[str, dict[str, Any]]:
        error: dict[str, Any] = {
            'code': self.code.value,
            'message': self.message,
            'field_errors': self.field_errors,
            'correlation_id': correlation_id,
            'retryable': self.retryable,
        }
        if self.current_version is not None:
            error['current_version'] = self.current_version
        return {'error': error}


class InvalidStateTransition(DomainError):
    def __init__(self, aggregate: str, current: str, target: str) -> None:
        super().__init__(
            DomainErrorCode.INVALID_STATE_TRANSITION,
            f'{aggregate.replace("_", " ").title()} cannot move from {current} to {target}.',
        )


class ImmutableRecord(DomainError):
    def __init__(self, aggregate: str, state: str) -> None:
        super().__init__(
            DomainErrorCode.IMMUTABLE_RECORD,
            f'{aggregate.replace("_", " ").title()} in {state} cannot be edited. '
            'Create a correction, amendment, or replacement version instead.',
        )


class MissingTransitionFields(DomainError):
    def __init__(self, fields: frozenset[str]) -> None:
        super().__init__(
            DomainErrorCode.MISSING_REQUIRED_RELATIONSHIP,
            'Required information is missing for this state change.',
            status_code=422,
            field_errors=[{'field': field, 'message': 'Required for this transition'} for field in sorted(fields)],
        )


class CrossTenantReference(DomainError):
    def __init__(self, relationship: str) -> None:
        super().__init__(
            DomainErrorCode.CROSS_TENANT_REFERENCE,
            f'{relationship} must belong to the authenticated organisation.',
        )


class AggregateOwnershipViolation(DomainError):
    def __init__(self, model_name: str, expected_service: str) -> None:
        super().__init__(
            DomainErrorCode.AGGREGATE_OWNERSHIP_VIOLATION,
            f'{model_name} may only be changed by the {expected_service} service.',
        )


class InvalidObjectReference(DomainError):
    def __init__(self, relationship: str, *, deleted: bool = False, archived: bool = False) -> None:
        if deleted:
            code = DomainErrorCode.DELETED_OBJECT_REFERENCE
            reason = 'has been deleted'
        elif archived:
            code = DomainErrorCode.ARCHIVED_OBJECT_REFERENCE
            reason = 'is archived'
        else:
            code = DomainErrorCode.MISSING_REQUIRED_RELATIONSHIP
            reason = 'does not exist'
        super().__init__(code, f'{relationship} {reason} in this organisation.')


class RegistryIntegrityError(DomainError):
    def __init__(self, code: DomainErrorCode, message: str) -> None:
        super().__init__(code, message)


class TransactionOwnershipViolation(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.TRANSACTION_OWNERSHIP_VIOLATION,
            'A business transaction is already active for this database session.',
            status_code=500,
        )


class PersistenceFailure(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.PERSISTENCE_FAILURE,
            'The operation could not be saved. No changes were applied.',
            status_code=500,
            retryable=True,
        )


class CorrectionReasonRequired(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.CORRECTION_REASON_REQUIRED,
            'A bounded reason code and explanation are required for this correction.',
            status_code=422,
        )


class CorrectionPermissionRequired(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.CORRECTION_PERMISSION_REQUIRED,
            'Elevated permission is required for this correction.',
            status_code=403,
        )


class InvalidCorrectionTarget(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.INVALID_CORRECTION_TARGET,
            'The correction target is unavailable in this organisation.',
        )


class CorrectionCycle(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.CORRECTION_CYCLE,
            'A correction cannot reference itself or create a correction cycle.',
        )


class HardDeleteForbidden(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.HARD_DELETE_FORBIDDEN,
            'Operational history cannot be permanently deleted.',
        )


class ConcurrentModification(DomainError):
    def __init__(self, current_version: int | None) -> None:
        super().__init__(
            DomainErrorCode.CONCURRENT_MODIFICATION,
            'The record changed before this correction could be applied.',
            current_version=current_version,
            retryable=True,
        )


class ExpectedVersionRequired(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.EXPECTED_VERSION_REQUIRED,
            'The current record version is required for this operation.',
            status_code=428,
        )


class InvalidExpectedVersion(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.INVALID_EXPECTED_VERSION,
            'The expected record version must be a positive integer.',
            status_code=400,
        )


class IdempotencyConflict(DomainError):
    def __init__(self, code: DomainErrorCode, message: str, *, retryable: bool = False) -> None:
        super().__init__(code, message, retryable=retryable)


class ActiveVersionConflict(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.ACTIVE_VERSION_CONFLICT,
            'Another active version won this operation. Refresh and try again.',
            retryable=True,
        )


class ArchiveConflict(DomainError):
    def __init__(self) -> None:
        super().__init__(
            DomainErrorCode.ARCHIVE_CONFLICT,
            'The record changed or gained an active dependency before it could be archived.',
            retryable=True,
        )
