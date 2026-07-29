from fastapi import APIRouter, Depends, Query
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


@router.get('/', response_model=list[schemas.AuditLog])
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.AUDIT_READ)),
):
    return crud.get_audit_logs(
        db=db,
        skip=skip,
        limit=limit,
        organisation_id=current_user.organisation_id,
    )
