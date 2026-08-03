from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AggregateContract:
    root: str
    owning_service: str
    owned_models: frozenset[str]

    def owns(self, model_name: str) -> bool:
        return model_name in self.owned_models


@runtime_checkable
class AggregateMutationService(Protocol):
    """Interface required of services that mutate an aggregate."""

    aggregate: str

    def transition(self, *, record_id: int, current: str, target: str, actor_id: int) -> object:
        ...


AGGREGATE_CONTRACTS = {
    'organisation': AggregateContract(
        'organisation', 'organisations', frozenset({'Organisation', 'CompanyPolicy'}),
    ),
    'customer': AggregateContract(
        'customer', 'customers', frozenset({'Customer', 'Contact(customer)'}),
    ),
    'site': AggregateContract(
        'site', 'sites', frozenset({
            'Site', 'Contact(site)', 'SiteAsset', 'PostOrder', 'PostOrderVersion',
            'PostOrderAcknowledgement', 'Checkpoint',
        }),
    ),
    'employee': AggregateContract(
        'employee', 'employees', frozenset({
            'Employee', 'EmployeeQualification', 'Licence', 'AvailabilityPeriod', 'LeavePeriod',
        }),
    ),
    'team': AggregateContract('team', 'teams', frozenset({'Team', 'TeamMember'})),
    'shift': AggregateContract('shift', 'shifts', frozenset({'Shift', 'ShiftAssignment'})),
    'patrol_template': AggregateContract(
        'patrol_template', 'patrol_templates', frozenset({'PatrolTemplate', 'PatrolTemplateCheckpoint'}),
    ),
    'patrol_occurrence': AggregateContract(
        'patrol_occurrence', 'patrol_occurrences',
        frozenset({'Patrol', 'PatrolAssignment', 'CheckpointVerificationEvent'}),
    ),
    'incident': AggregateContract('incident', 'incidents', frozenset({'Alert'})),
    'operational_alert': AggregateContract(
        'operational_alert', 'operational_alerts', frozenset({'OperationalAlert'}),
    ),
    'notification': AggregateContract('notification', 'notifications', frozenset({'Notification'})),
    'evidence': AggregateContract(
        'evidence', 'evidence', frozenset({'EvidenceAttachment', 'EvidenceLink'}),
    ),
    'daily_activity_report': AggregateContract(
        'daily_activity_report', 'daily_activity_reports', frozenset({'DailyActivityReport'}),
    ),
    'operational_event': AggregateContract(
        'operational_event', 'operational_events', frozenset({'AuditLog', 'OperationalEventSubject'}),
    ),
}


def owning_contract(aggregate: str) -> AggregateContract:
    try:
        return AGGREGATE_CONTRACTS[aggregate]
    except KeyError as exc:
        raise ValueError(f'Unknown aggregate contract: {aggregate}') from exc
