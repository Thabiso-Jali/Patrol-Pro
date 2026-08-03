from dataclasses import dataclass

from .errors import (
    CorrectionPermissionRequired,
    CorrectionReasonRequired,
    InvalidCorrectionTarget,
)
from .registry import DomainObjectType


MAX_REASON_CODE_LENGTH = 64
MAX_EXPLANATION_LENGTH = 1000
MAX_CORRELATION_ID_LENGTH = 128


@dataclass(frozen=True)
class CorrectionCommand:
    target_type: DomainObjectType
    target_id: int
    correction_type: str
    reason_code: str
    explanation: str
    actor_user_id: int | None
    actor_employee_id: int | None
    organisation_id: int
    permission: str
    granted_permissions: frozenset[str]
    correlation_id: str
    expected_record_version: int | None = None
    expected_state: str | None = None
    original_id: int | None = None

    def validate(self) -> None:
        try:
            DomainObjectType(self.target_type)
        except ValueError as exc:
            raise InvalidCorrectionTarget() from exc
        if self.target_id <= 0 or self.organisation_id <= 0:
            raise InvalidCorrectionTarget()
        if not self.reason_code.strip() or not self.explanation.strip():
            raise CorrectionReasonRequired()
        if len(self.reason_code) > MAX_REASON_CODE_LENGTH or len(self.explanation) > MAX_EXPLANATION_LENGTH:
            raise CorrectionReasonRequired()
        if not self.correlation_id.strip() or len(self.correlation_id) > MAX_CORRELATION_ID_LENGTH:
            raise CorrectionReasonRequired()
        if self.actor_user_id is None and self.actor_employee_id is None:
            raise CorrectionPermissionRequired()
        if self.permission not in self.granted_permissions:
            raise CorrectionPermissionRequired()

    def event_metadata(self) -> dict[str, str | int]:
        return {
            'correction_type': self.correction_type,
            'reason_code': self.reason_code.strip(),
            'explanation': self.explanation.strip(),
            'target_type': DomainObjectType(self.target_type).value,
            'target_id': self.target_id,
        }
