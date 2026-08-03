"""Internal idempotency ledger for retry-prone business commands."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Generic, TypeVar
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..domain.errors import DomainErrorCode, IdempotencyConflict
from .transactions import require_transaction
from .tenant_validation import aggregate_mutation

T = TypeVar('T')
_KEY_RE = re.compile(r'^[A-Za-z0-9._~:+/=\-]{1,128}$')
_RETENTION_DAYS = 30


@dataclass(frozen=True)
class IdempotencyResult(Generic[T]):
    value: T
    replayed: bool


def normalize_key(key: str | None) -> str | None:
    if key is None:
        return None
    normalized = key.strip()
    if not _KEY_RE.fullmatch(normalized):
        raise IdempotencyConflict(
            DomainErrorCode.IDEMPOTENCY_KEY_REUSED,
            'Idempotency-Key must contain 1–128 safe printable characters.',
        )
    return normalized


def request_fingerprint(payload: Any) -> str:
    """Hash canonical allow-listed command data; never persist the body itself."""
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _claim(
    db: Session, *, organisation_id: int, actor_user_id: int | None,
    actor_scope: str, command_type: str, key: str, fingerprint: str,
    correlation_id: str,
) -> tuple[models.IdempotencyRecord, bool]:
    values = dict(
        organisation_id=organisation_id, actor_user_id=actor_user_id,
        actor_scope=actor_scope, command_type=command_type, idempotency_key=key,
        request_fingerprint=fingerprint, processing_state='pending',
        correlation_id=correlation_id, created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=_RETENTION_DAYS),
        record_version=1,
    )
    inserted = False
    with aggregate_mutation(db, 'idempotency'):
        if db.bind and db.bind.dialect.name == 'postgresql':
            statement = pg_insert(models.IdempotencyRecord).values(**values).on_conflict_do_nothing(
                constraint='uq_idempotency_command_scope',
            ).returning(models.IdempotencyRecord.id)
            inserted_id = db.execute(statement).scalar_one_or_none()
            inserted = inserted_id is not None
        else:
            existing = db.query(models.IdempotencyRecord.id).filter_by(
                organisation_id=organisation_id, actor_scope=actor_scope,
                command_type=command_type, idempotency_key=key,
            ).first()
            if existing is None:
                record = models.IdempotencyRecord(**values)
                db.add(record)
                try:
                    db.flush()
                    inserted = True
                except IntegrityError as exc:
                    raise IdempotencyConflict(
                        DomainErrorCode.IDEMPOTENCY_IN_PROGRESS,
                        'An identical command is already in progress.', retryable=True,
                    ) from exc
    record = db.query(models.IdempotencyRecord).filter_by(
        organisation_id=organisation_id, actor_scope=actor_scope,
        command_type=command_type, idempotency_key=key,
    ).with_for_update().one()
    return record, inserted


def execute_idempotent(
    db: Session, *, organisation_id: int, actor_user_id: int | None,
    command_type: str, key: str | None, fingerprint_payload: Any,
    execute: Callable[[], T], replay: Callable[[dict[str, Any]], T],
    result_metadata: Callable[[T], dict[str, Any]], actor_scope: str | None = None,
    correlation_id: str | None = None,
) -> IdempotencyResult[T]:
    require_transaction(db)
    normalized = normalize_key(key)
    if normalized is None:
        return IdempotencyResult(execute(), False)
    scope = actor_scope or (f'user:{actor_user_id}' if actor_user_id is not None else 'trusted-system')
    fingerprint = request_fingerprint(fingerprint_payload)
    record, inserted = _claim(
        db, organisation_id=organisation_id, actor_user_id=actor_user_id,
        actor_scope=scope, command_type=command_type, key=normalized,
        fingerprint=fingerprint, correlation_id=correlation_id or str(uuid4()),
    )
    if record.request_fingerprint != fingerprint:
        raise IdempotencyConflict(
            DomainErrorCode.IDEMPOTENCY_KEY_REUSED,
            'This idempotency key was already used for a different command.',
        )
    if not inserted:
        if record.processing_state == 'completed':
            return IdempotencyResult(replay(record.response_metadata or {}), True)
        if record.processing_state == 'pending':
            raise IdempotencyConflict(
                DomainErrorCode.IDEMPOTENCY_IN_PROGRESS,
                'This command is already in progress.', retryable=True,
            )
        if record.processing_state == 'failed' and record.failure_code:
            with aggregate_mutation(db, 'idempotency'):
                record.processing_state = 'pending'
                record.failure_code = None
                record.record_version += 1
                db.flush()
    value = execute()
    metadata = result_metadata(value)
    encoded = json.dumps(metadata, sort_keys=True, default=str)
    if len(encoded) > 4096:
        raise ValueError('Idempotency result metadata exceeds the safe limit')
    with aggregate_mutation(db, 'idempotency'):
        record.processing_state = 'completed'
        record.response_metadata = metadata
        record.completed_at = datetime.now(timezone.utc)
        record.record_version += 1
        db.flush()
    return IdempotencyResult(value, False)
