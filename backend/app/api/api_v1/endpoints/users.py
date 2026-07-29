from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .... import schemas
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
