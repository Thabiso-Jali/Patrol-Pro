import pytest

from backend.app.domain.aggregates import AGGREGATE_CONTRACTS, owning_contract
from backend.app.domain.errors import (
    DomainErrorCode,
    ImmutableRecord,
    InvalidStateTransition,
    MissingTransitionFields,
)
from backend.app.domain.states import STATE_MACHINES, assert_transition, validate_state_change
from backend.app.permissions import Permission


EXPECTED_STATE_MACHINES = {
    'organisation', 'customer', 'site', 'employee', 'team', 'company_policy',
    'post_order_version', 'qualification', 'licence', 'availability', 'leave',
    'shift', 'shift_assignment', 'patrol_template', 'patrol_occurrence',
    'checkpoint', 'verification_event', 'incident', 'operational_alert',
    'notification_delivery', 'evidence_attachment', 'daily_activity_report',
}


def test_every_approved_lifecycle_has_one_executable_contract():
    permission_values = {permission.value for permission in Permission}
    assert set(STATE_MACHINES) == EXPECTED_STATE_MACHINES
    for name, machine in STATE_MACHINES.items():
        assert machine.states, name
        for source, targets in machine.transitions.items():
            assert source in machine.states
            for target, rule in targets.items():
                assert target in machine.states
                assert rule.permission in permission_values
                assert rule.event
                assert rule.concurrency in {'optimistic', 'row_lock', 'append_only'}


def test_aggregate_contracts_have_one_owner_and_do_not_overlap_internal_models():
    owners = {}
    for aggregate, contract in AGGREGATE_CONTRACTS.items():
        assert contract.root == aggregate
        assert contract.owning_service
        for model_name in contract.owned_models:
            assert model_name not in owners, f'{model_name} owned by two aggregates'
            owners[model_name] = aggregate
    assert owning_contract('patrol_occurrence').owns('CheckpointVerificationEvent')
    with pytest.raises(ValueError):
        owning_contract('unknown')


def test_shared_transition_validator_returns_authoritative_rule():
    rule = validate_state_change('shift', 'draft', 'published')
    assert rule.permission == 'patrols.manage'
    assert rule.event == 'shift.published'


def test_impossible_unknown_and_terminal_transitions_use_stable_domain_errors():
    with pytest.raises(InvalidStateTransition) as invalid:
        assert_transition('shift', 'draft', 'completed')
    assert invalid.value.code == DomainErrorCode.INVALID_STATE_TRANSITION
    with pytest.raises(InvalidStateTransition):
        assert_transition('shift', 'not-a-state', 'published')
    with pytest.raises(ImmutableRecord) as immutable:
        validate_state_change('incident', 'resolved', 'resolved')
    assert immutable.value.code == DomainErrorCode.IMMUTABLE_RECORD


def test_transition_required_fields_are_defined_in_the_state_contract():
    with pytest.raises(MissingTransitionFields) as missing:
        assert_transition('incident', 'open', 'resolved')
    assert missing.value.field_errors == [
        {'field': 'resolution_notes', 'message': 'Required for this transition'},
    ]
    assert_transition(
        'incident', 'open', 'resolved',
        provided_fields=frozenset({'resolution_notes'}),
    )


def test_domain_error_envelope_is_stable_safe_and_actionable():
    envelope = InvalidStateTransition('shift', 'draft', 'completed').envelope('correlation-1')
    assert envelope == {
        'error': {
            'code': 'INVALID_STATE_TRANSITION',
            'message': 'Shift cannot move from draft to completed.',
            'field_errors': [],
            'correlation_id': 'correlation-1',
            'retryable': False,
        },
    }
