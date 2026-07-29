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


@router.get('/summary', response_model=schemas.OperationsSummary)
def get_operations_summary(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.DASHBOARD_VIEW)),
):
    return crud.get_operations_summary(db=db, organisation_id=current_user.organisation_id)
