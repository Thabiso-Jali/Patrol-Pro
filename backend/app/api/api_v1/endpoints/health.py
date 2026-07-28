from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from ....database import SessionLocal
from ....security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get('/health')
def health_check_public(response: Response, db: Session = Depends(get_db)):
    """Database readiness check without exposing internal errors."""
    try:
        db.execute(text("SELECT 1"))
        return {
            'status': 'ready',
            'service': 'patrol-pro-api',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        logger.exception("Database readiness check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            'status': 'unavailable',
            'service': 'patrol-pro-api',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }


@router.get('/status')
def status_check(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Protected status endpoint with detailed information."""
    try:
        db.execute(text("SELECT 1"))
        return {
            'status': 'ok',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': 'connected',
            'user': current_user.email,
        }
    except Exception:
        logger.exception("Authenticated status check failed")
        return {
            'status': 'error',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
