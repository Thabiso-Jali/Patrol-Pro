from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .corrections import CorrectionCommand
from .errors import CorrectionCycle, HardDeleteForbidden, ImmutableRecord, InvalidStateTransition
from .states import STATE_MACHINES


@dataclass(frozen=True)
class ImmutabilityPolicy:
    machine: str | None = None
    state_column: str = 'status'
    append_only: bool = False
    hard_delete_forbidden: bool = True
    immutable_identity_fields: frozenset[str] = frozenset()


POLICIES = {
    'Organisation': ImmutabilityPolicy(hard_delete_forbidden=True),
    'Customer': ImmutabilityPolicy(hard_delete_forbidden=True),
    'Site': ImmutabilityPolicy(hard_delete_forbidden=True),
    'Employee': ImmutabilityPolicy(hard_delete_forbidden=True),
    'Team': ImmutabilityPolicy(hard_delete_forbidden=True),
    'CompanyPolicy': ImmutabilityPolicy('company_policy'),
    'PostOrderVersion': ImmutabilityPolicy('post_order_version'),
    'Shift': ImmutabilityPolicy('shift'),
    'ShiftAssignment': ImmutabilityPolicy('shift_assignment'),
    'PatrolTemplate': ImmutabilityPolicy('patrol_template'),
    'Patrol': ImmutabilityPolicy('patrol_occurrence', 'lifecycle_status'),
    'Alert': ImmutabilityPolicy('incident'),
    'OperationalAlert': ImmutabilityPolicy('operational_alert'),
    'Notification': ImmutabilityPolicy('notification_delivery', 'delivery_status'),
    'EvidenceAttachment': ImmutabilityPolicy(
        'evidence_attachment', immutable_identity_fields=frozenset({
            'storage_key', 'content_hash', 'media_type', 'byte_size', 'original_filename',
        }),
    ),
    'DailyActivityReport': ImmutabilityPolicy('daily_activity_report'),
    'CheckpointVerificationEvent': ImmutabilityPolicy(append_only=True),
    'AuditLog': ImmutabilityPolicy(append_only=True),
    'OperationalEventSubject': ImmutabilityPolicy(append_only=True),
    'EvidenceLink': ImmutabilityPolicy(append_only=True),
    'PostOrderAcknowledgement': ImmutabilityPolicy(append_only=True),
    'DomainObject': ImmutabilityPolicy(),
    'PostOrder': ImmutabilityPolicy(),
    'Checkpoint': ImmutabilityPolicy(
        hard_delete_forbidden=False,
        immutable_identity_fields=frozenset({'verified_at', 'verified_by'}),
    ),
}

_APPROVED_KEY = 'patrol_pro_approved_immutable_mutations'


@contextmanager
def approved_correction(db: Session, instance, command: CorrectionCommand) -> Iterator[None]:
    command.validate()
    key = id(instance)
    approved = db.info.setdefault(_APPROVED_KEY, {})
    approved[key] = command
    try:
        yield
    finally:
        approved.pop(key, None)
        if not approved:
            db.info.pop(_APPROVED_KEY, None)


@contextmanager
def approved_projection(db: Session, instance) -> Iterator[None]:
    approved = db.info.setdefault(_APPROVED_KEY, {})
    approved[id(instance)] = 'compatibility_projection'
    try:
        yield
    finally:
        approved.pop(id(instance), None)
        if not approved:
            db.info.pop(_APPROVED_KEY, None)


def _original_value(state, column):
    history = state.attrs[column].history
    if history.deleted:
        return history.deleted[0]
    return getattr(state.object, column)


def _validate_transition(instance, policy, state) -> None:
    if not policy.machine or instance in state.session.new:
        return
    history = state.attrs[policy.state_column].history
    if not history.has_changes() or not history.deleted:
        return
    current, target = history.deleted[0], getattr(instance, policy.state_column)
    machine = STATE_MACHINES[policy.machine]
    if target not in machine.transitions.get(current, {}):
        raise InvalidStateTransition(policy.machine, current, target)


def enforce_immutability(db: Session) -> None:
    approved = db.info.get(_APPROVED_KEY, {})
    for instance in db.deleted:
        policy = POLICIES.get(type(instance).__name__)
        if policy and policy.hard_delete_forbidden:
            raise HardDeleteForbidden()

    for instance in db.dirty:
        policy = POLICIES.get(type(instance).__name__)
        if not policy:
            continue
        state = inspect(instance)
        if not state.modified:
            continue
        if policy.append_only:
            raise ImmutableRecord(type(instance).__name__, 'append-only')
        if id(instance) not in approved:
            _validate_transition(instance, policy, state)
        original_state = _original_value(state, policy.state_column) if policy.machine else None
        immutable = policy.machine and original_state in STATE_MACHINES[policy.machine].immutable_states
        identity_changed = any(state.attrs[field].history.has_changes() for field in policy.immutable_identity_fields)
        if type(instance).__name__ == 'Checkpoint':
            status_history = state.attrs.status.history
            identity_changed = identity_changed or (
                status_history.has_changes() and getattr(instance, 'status', None) == 'verified'
            )
        if (immutable or identity_changed) and id(instance) not in approved:
            raise ImmutableRecord(policy.machine or type(instance).__name__, original_state or 'accepted')

        for correction_field in ('correction_of_id', 'original_event_id'):
            if hasattr(instance, correction_field):
                reference = getattr(instance, correction_field)
                if reference is not None and reference == getattr(instance, 'id', None):
                    raise CorrectionCycle()
