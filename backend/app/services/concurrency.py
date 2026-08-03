"""Canonical optimistic-version and narrow row-lock controls."""

from collections.abc import Iterable
import re
from typing import TypeVar

from sqlalchemy.orm import Session

from ..domain.errors import (
    ConcurrentModification,
    ExpectedVersionRequired,
    InvalidExpectedVersion,
    InvalidObjectReference,
)
from .transactions import require_transaction

T = TypeVar('T')
_EXPECTED_VERSION_RE = re.compile(r'^(?:[1-9][0-9]*|"[1-9][0-9]*"|W/"[1-9][0-9]*")$')


def parse_expected_version(value: str | int | None, *, required: bool = False) -> int | None:
    if value is None or value == '':
        if required:
            raise ExpectedVersionRequired()
        return None
    if isinstance(value, bool):
        raise InvalidExpectedVersion()
    if isinstance(value, str):
        value = value.strip()
        if len(value) > 32 or not _EXPECTED_VERSION_RE.fullmatch(value):
            raise InvalidExpectedVersion()
        if value.startswith('W/'):
            value = value[2:]
        if value.startswith('"'):
            value = value[1:-1]
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidExpectedVersion() from exc
    if parsed < 1:
        raise InvalidExpectedVersion()
    return parsed


def lock_tenant_record(
    db: Session, model: type[T], *, record_id: int, organisation_id: int,
    relationship: str = 'Record', allow_archived: bool = True,
) -> T:
    """Lock a scoped row; never probe outside the authenticated tenant."""
    require_transaction(db)
    query = db.query(model).filter(
        model.id == record_id,
        model.organisation_id == organisation_id,
    )
    record = query.populate_existing().with_for_update().one_or_none()
    if record is None:
        raise InvalidObjectReference(relationship)
    if getattr(record, 'is_deleted', False):
        raise InvalidObjectReference(relationship, deleted=True)
    if not allow_archived:
        if getattr(record, 'status', None) in {'inactive', 'archived'}:
            raise InvalidObjectReference(relationship, archived=True)
    return record


def lock_tenant_records(
    db: Session, model: type[T], *, record_ids: Iterable[int], organisation_id: int,
) -> list[T]:
    require_transaction(db)
    ids = sorted(set(record_ids))
    if not ids:
        return []
    return db.query(model).filter(
        model.organisation_id == organisation_id,
        model.id.in_(ids),
    ).order_by(model.id).populate_existing().with_for_update().all()


def assert_expected_version(record, expected_version: int | None, *, required: bool = False) -> None:
    expected = parse_expected_version(expected_version, required=required)
    if expected is not None and record.record_version != expected:
        raise ConcurrentModification(record.record_version)


def advance_version(record, expected_version: int | None = None, *, required: bool = False) -> int:
    assert_expected_version(record, expected_version, required=required)
    record.record_version += 1
    return record.record_version
