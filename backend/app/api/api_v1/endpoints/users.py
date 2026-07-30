from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .... import models, schemas
from ....database import SessionLocal
from ....permissions import Permission
from ....security import require_permissions

router = APIRouter()
OPERATIONAL_ROLES = {
    schemas.UserRole.officer.value,
    schemas.UserRole.employee.value,
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post('/', response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.USERS_MANAGE)),
):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail='Direct employee creation is disabled; use the invitations endpoint',
    )


@router.get('/officers', response_model=list[schemas.User])
def list_officers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permissions(Permission.USERS_VIEW)),
):
    return (
        db.query(models.User)
        .filter(
            models.User.organisation_id == current_user.organisation_id,
            models.User.role.in_(OPERATIONAL_ROLES),
            models.User.is_active.is_(True),
            models.User.is_deleted.is_(False),
        )
        .order_by(models.User.full_name.asc(), models.User.id.asc())
        .all()
    )
