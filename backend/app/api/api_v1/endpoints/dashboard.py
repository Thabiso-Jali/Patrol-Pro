from fastapi import APIRouter, Depends, HTTPException
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


@router.get('/stats', response_model=schemas.DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.DASHBOARD_VIEW)),
):
    if current_user.organisation_id is None:
        raise HTTPException(status_code=403, detail='Organisation membership is required')
    return crud.get_dashboard_stats(db=db, organisation_id=current_user.organisation_id)
