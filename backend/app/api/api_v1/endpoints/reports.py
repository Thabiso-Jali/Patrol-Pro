from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .... import crud, schemas
from ....database import SessionLocal
from ....permissions import Permission
from ....security import require_permissions

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get('/analytics', response_model=schemas.AnalyticsReport)
def get_analytics_report(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.REPORTS_READ)),
):
    return crud.get_analytics_report(db=db, organisation_id=current_user.organisation_id)
