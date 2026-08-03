from dataclasses import dataclass, field

from .errors import ImmutableRecord, InvalidStateTransition, MissingTransitionFields


@dataclass(frozen=True)
class TransitionRule:
    permission: str
    event: str
    required_fields: frozenset[str] = frozenset()
    concurrency: str = 'optimistic'


@dataclass(frozen=True)
class StateMachine:
    transitions: dict[str, dict[str, TransitionRule]]
    immutable_states: frozenset[str] = frozenset()
    correction_process: str = 'correction'
    states: frozenset[str] = field(init=False)

    def __post_init__(self):
        targets = {target for transitions in self.transitions.values() for target in transitions}
        object.__setattr__(self, 'states', frozenset(self.transitions) | frozenset(targets))


def _rules(permission: str, event_prefix: str, graph: dict[str, set[str]]) -> dict[str, dict[str, TransitionRule]]:
    return {
        current: {
            target: TransitionRule(permission, f'{event_prefix}.{target}')
            for target in targets
        }
        for current, targets in graph.items()
    }


def _machine(permission, event_prefix, graph, immutable=(), correction='correction'):
    return StateMachine(
        _rules(permission, event_prefix, graph), frozenset(immutable), correction,
    )


STATE_MACHINES = {
    'organisation': _machine('company.manage', 'organisation', {
        'active': {'suspended', 'archived'}, 'suspended': {'active', 'archived'}, 'archived': set(),
    }, {'archived'}),
    'customer': _machine('customers.manage', 'customer', {
        'active': {'inactive', 'archived'}, 'inactive': {'active', 'archived'}, 'archived': set(),
    }, {'archived'}),
    'site': _machine('customers.manage', 'site', {
        'draft': {'active', 'archived'}, 'active': {'inactive', 'archived'},
        'inactive': {'active', 'archived'}, 'archived': set(),
    }, {'archived'}),
    'employee': _machine('users.manage', 'employee', {
        'pending': {'active', 'archived'}, 'active': {'inactive', 'archived'},
        'inactive': {'active', 'archived'}, 'archived': set(),
    }, {'archived'}),
    'team': _machine('users.manage', 'team', {
        'active': {'inactive', 'archived'}, 'inactive': {'active', 'archived'}, 'archived': set(),
    }, {'archived'}),
    'company_policy': _machine('company.manage', 'company_policy', {
        'draft': {'approved', 'archived'}, 'approved': {'active', 'archived'},
        'active': {'superseded', 'archived'}, 'superseded': {'archived'}, 'archived': set(),
    }, {'active', 'superseded', 'archived'}, 'replacement_version'),
    'post_order_version': _machine('company.manage', 'post_order', {
        'draft': {'approved', 'archived'}, 'approved': {'active', 'archived'},
        'active': {'superseded', 'archived'}, 'superseded': {'archived'}, 'archived': set(),
    }, {'active', 'superseded', 'archived'}, 'replacement_version'),
    'qualification': _machine('users.manage', 'qualification', {
        'active': {'retired'}, 'retired': set(),
    }, {'retired'}),
    'licence': _machine('users.manage', 'licence', {
        'pending': {'valid', 'revoked'}, 'valid': {'expired', 'revoked'},
        'expired': set(), 'revoked': set(),
    }, {'expired', 'revoked'}),
    'availability': _machine('users.manage', 'availability', {
        'proposed': {'confirmed', 'cancelled'}, 'confirmed': {'expired', 'cancelled'},
        'expired': set(), 'cancelled': set(),
    }, {'expired', 'cancelled'}),
    'leave': _machine('users.manage', 'leave', {
        'requested': {'approved', 'rejected', 'cancelled'},
        'approved': {'cancelled'}, 'rejected': set(), 'cancelled': set(),
    }, {'rejected', 'cancelled'}, 'amendment'),
    'shift': _machine('patrols.manage', 'shift', {
        'draft': {'published', 'cancelled'}, 'published': {'active', 'cancelled'},
        'active': {'completed', 'cancelled'}, 'completed': {'archived'},
        'cancelled': {'archived'}, 'archived': set(),
    }, {'completed', 'cancelled', 'archived'}, 'amendment'),
    'shift_assignment': _machine('patrols.manage', 'shift_assignment', {
        'proposed': {'confirmed', 'cancelled'}, 'confirmed': {'active', 'cancelled'},
        'active': {'completed', 'cancelled'}, 'completed': set(), 'cancelled': set(),
    }, {'completed', 'cancelled'}, 'correction'),
    'patrol_template': _machine('patrols.manage', 'patrol_template', {
        'draft': {'active', 'retired'}, 'active': {'superseded', 'retired'},
        'superseded': set(), 'retired': set(),
    }, {'active', 'superseded', 'retired'}, 'replacement_version'),
    'patrol_occurrence': _machine('patrols.manage', 'patrol', {
        'draft': {'scheduled', 'cancelled'}, 'scheduled': {'in_progress', 'missed', 'cancelled'},
        'in_progress': {'completed', 'cancelled'}, 'completed': {'archived'},
        'missed': {'archived'}, 'cancelled': {'archived'}, 'archived': set(),
    }, {'completed', 'missed', 'cancelled', 'archived'}, 'amendment'),
    'checkpoint': _machine('checkpoints.manage', 'checkpoint', {
        'active': {'inactive', 'archived'}, 'inactive': {'active', 'archived'}, 'archived': set(),
    }, {'archived'}),
    'verification_event': _machine('checkpoints.verify', 'checkpoint_verification', {
        'recorded': set(), 'corrected': set(),
    }, {'recorded', 'corrected'}, 'correction_event'),
    'incident': _machine('incidents.manage', 'incident', {
        'open': {'investigating', 'resolved', 'cancelled'},
        'investigating': {'resolved', 'cancelled'}, 'resolved': set(), 'cancelled': set(),
    }, {'resolved', 'cancelled'}, 'controlled_reopening'),
    'operational_alert': _machine('operations.write', 'operational_alert', {
        'open': {'acknowledged', 'resolved', 'expired'},
        'acknowledged': {'resolved', 'expired'}, 'resolved': set(), 'expired': set(),
    }, {'resolved', 'expired'}),
    'notification_delivery': _machine('notifications.manage', 'notification', {
        'queued': {'sent', 'failed'}, 'sent': {'delivered', 'failed'},
        'delivered': {'read'}, 'failed': set(), 'read': set(),
    }, {'failed', 'read'}),
    'evidence_attachment': _machine('operations.write', 'evidence', {
        'pending': {'uploading', 'failed'}, 'uploading': {'available', 'quarantined', 'failed'},
        'available': {'superseded'}, 'quarantined': {'available', 'failed'},
        'failed': set(), 'superseded': set(),
    }, {'available', 'failed', 'superseded'}, 'replacement_attachment'),
    'daily_activity_report': _machine('reports.read', 'daily_activity_report', {
        'draft': {'generated'}, 'generated': {'approved', 'superseded'},
        'approved': {'delivered', 'superseded'}, 'delivered': {'superseded'}, 'superseded': set(),
    }, {'generated', 'approved', 'delivered', 'superseded'}, 'superseding_revision'),
}

# Resolution/cancellation must carry the authoritative explanation.
for source in ('open', 'investigating'):
    for target in ('resolved', 'cancelled'):
        rule = STATE_MACHINES['incident'].transitions[source][target]
        STATE_MACHINES['incident'].transitions[source][target] = TransitionRule(
            rule.permission, rule.event, frozenset({'resolution_notes'}), rule.concurrency,
        )


def transition_rule(machine_name: str, current: str, target: str) -> TransitionRule:
    machine = STATE_MACHINES.get(machine_name)
    if machine is None or current not in machine.states or target not in machine.states:
        raise InvalidStateTransition(machine_name, current, target)
    try:
        return machine.transitions[current][target]
    except KeyError as exc:
        raise InvalidStateTransition(machine_name, current, target) from exc


def assert_transition(
    machine_name: str,
    current: str,
    target: str,
    *,
    provided_fields: frozenset[str] = frozenset(),
) -> TransitionRule:
    rule = transition_rule(machine_name, current, target)
    missing = rule.required_fields - provided_fields
    if missing:
        raise MissingTransitionFields(missing)
    return rule


def assert_mutable(machine_name: str, state: str) -> None:
    machine = STATE_MACHINES.get(machine_name)
    if machine is None or state not in machine.states:
        raise InvalidStateTransition(machine_name, state, state)
    if state in machine.immutable_states:
        raise ImmutableRecord(machine_name, state)


def validate_state_change(
    machine_name: str,
    current: str,
    target: str,
    *,
    provided_fields: frozenset[str] = frozenset(),
) -> TransitionRule | None:
    if current == target:
        assert_mutable(machine_name, current)
        return None
    return assert_transition(
        machine_name, current, target, provided_fields=provided_fields,
    )
