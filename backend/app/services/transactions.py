from contextlib import contextmanager
from typing import Iterator

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..domain.errors import DomainError, PersistenceFailure, TransactionOwnershipViolation


_TRANSACTION_OWNER_KEY = 'patrol_pro_transaction_owner'


def require_transaction(db: Session) -> None:
    if not db.info.get(_TRANSACTION_OWNER_KEY):
        raise TransactionOwnershipViolation()


@contextmanager
def transactional(db: Session, *, owner: str = 'application') -> Iterator[Session]:
    """Own one complete business command, including projections and events."""
    if db.info.get(_TRANSACTION_OWNER_KEY):
        raise TransactionOwnershipViolation()
    db.info[_TRANSACTION_OWNER_KEY] = owner
    try:
        yield db
        db.flush()
        db.commit()
    except (DomainError, HTTPException, RequestValidationError):
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise PersistenceFailure() from exc
    except Exception as exc:
        db.rollback()
        raise PersistenceFailure() from exc
    except BaseException:
        db.rollback()
        raise
    finally:
        db.info.pop(_TRANSACTION_OWNER_KEY, None)


def transactional_session() -> Iterator[Session]:
    """FastAPI/background-compatible session dependency for one business command."""
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        with transactional(db, owner='request'):
            yield db
    finally:
        db.close()
