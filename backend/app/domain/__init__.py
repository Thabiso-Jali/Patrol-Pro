"""Canonical Patrol Pro domain contracts."""

from .registry import DOMAIN_OBJECT_OWNERS, DomainObjectType
from .corrections import CorrectionCommand
from .aggregates import AGGREGATE_CONTRACTS, AggregateContract, AggregateMutationService
from .errors import DomainError, DomainErrorCode
from .states import STATE_MACHINES, assert_transition, validate_state_change

__all__ = [
    'AGGREGATE_CONTRACTS', 'AggregateContract', 'AggregateMutationService',
    'DOMAIN_OBJECT_OWNERS', 'DomainObjectType', 'CorrectionCommand', 'DomainError', 'DomainErrorCode',
    'STATE_MACHINES', 'assert_transition', 'validate_state_change',
]
