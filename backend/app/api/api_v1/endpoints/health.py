from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ....database import SessionLocal
from ....security import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get('/health')
def health_check_public(db: Session = Depends(get_db)):
    """Public health check endpoint."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'error',
            'error': str(e),
        }


@router.get('/status')
def status_check(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Protected status endpoint with detailed information."""
    try:
        db.execute("SELECT 1")
        return {
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'user': current_user.email,
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
        }
