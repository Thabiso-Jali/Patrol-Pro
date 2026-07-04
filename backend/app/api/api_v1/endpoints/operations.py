from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .... import crud, schemas
from ....database import SessionLocal
from ....security import get_current_user

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
    current_user: schemas.User = Depends(get_current_user),
):
    return crud.get_operations_summary(db=db, organisation_id=current_user.organisation_id)
