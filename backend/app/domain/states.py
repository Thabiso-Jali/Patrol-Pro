from dataclasses import dataclass


class InvalidStateTransition(ValueError):
    pass


@dataclass(frozen=True)
class StateMachine:
    transitions: dict[str, frozenset[str]]
    immutable_states: frozenset[str] = frozenset()


STATE_MACHINES = {
    'site': StateMachine({
        'draft': frozenset({'active', 'archived'}),
        'active': frozenset({'inactive', 'archived'}),
        'inactive': frozenset({'active', 'archived'}),
        'archived': frozenset(),
    }),
    'employee': StateMachine({
        'pending': frozenset({'active', 'archived'}),
        'active': frozenset({'inactive', 'archived'}),
        'inactive': frozenset({'active', 'archived'}),
        'archived': frozenset(),
    }),
    'shift': StateMachine({
        'draft': frozenset({'published', 'cancelled'}),
        'published': frozenset({'active', 'cancelled'}),
        'active': frozenset({'completed', 'cancelled'}),
        'completed': frozenset({'archived'}),
        'cancelled': frozenset({'archived'}),
        'archived': frozenset(),
    }, frozenset({'completed', 'cancelled', 'archived'})),
    'patrol_occurrence': StateMachine({
        'draft': frozenset({'scheduled', 'cancelled'}),
        'scheduled': frozenset({'in_progress', 'missed', 'cancelled'}),
        'in_progress': frozenset({'completed', 'cancelled'}),
        'completed': frozenset({'archived'}),
        'missed': frozenset({'archived'}),
        'cancelled': frozenset({'archived'}),
        'archived': frozenset(),
    }, frozenset({'completed', 'missed', 'cancelled', 'archived'})),
    'incident': StateMachine({
        'open': frozenset({'investigating', 'resolved', 'cancelled'}),
        'investigating': frozenset({'resolved', 'cancelled'}),
        'resolved': frozenset(),
        'cancelled': frozenset(),
    }, frozenset({'resolved', 'cancelled'})),
    'versioned_document': StateMachine({
        'draft': frozenset({'approved', 'archived'}),
        'approved': frozenset({'active', 'archived'}),
        'active': frozenset({'superseded', 'archived'}),
        'superseded': frozenset({'archived'}),
        'archived': frozenset(),
    }, frozenset({'active', 'superseded', 'archived'})),
    'daily_activity_report': StateMachine({
        'draft': frozenset({'generated'}),
        'generated': frozenset({'approved', 'superseded'}),
        'approved': frozenset({'delivered', 'superseded'}),
        'delivered': frozenset({'superseded'}),
        'superseded': frozenset(),
    }, frozenset({'generated', 'approved', 'delivered', 'superseded'})),
}


def assert_transition(machine_name: str, current: str, target: str) -> None:
    machine = STATE_MACHINES[machine_name]
    if target not in machine.transitions.get(current, frozenset()):
        raise InvalidStateTransition(f'Illegal {machine_name} transition: {current} -> {target}')


def assert_mutable(machine_name: str, state: str) -> None:
    if state in STATE_MACHINES[machine_name].immutable_states:
        raise InvalidStateTransition(
            f'{machine_name} in {state} is immutable; create a correction, amendment, or revision'
        )
