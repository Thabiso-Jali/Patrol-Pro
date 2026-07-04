from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .... import crud, schemas
from ....database import SessionLocal
from ....security import get_password_hash, require_roles
from ....services.audit import log_audit_event

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
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin)),
):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    hashed_password = get_password_hash(user.password)
    created = crud.create_user(
        db=db,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role.value,
        created_by=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='user.create',
        entity_type='user',
        entity_id=str(created.id),
    )
    return created
