from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .... import crud, models, schemas
from ....config import get_settings
from ....database import SessionLocal
from ....security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
)
from ....services.audit import log_audit_event

router = APIRouter()
settings = get_settings()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post('/token', response_model=schemas.Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.email, 'role': user.role}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={'sub': user.email, 'role': user.role})
    log_audit_event(
        db,
        actor_user_id=user.id,
        actor_email=user.email,
        action='auth.login',
        entity_type='user',
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'access_token_expires_minutes': settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@router.post('/refresh', response_model=schemas.Token)
def refresh_access_token(payload: schemas.RefreshTokenRequest):
    token_data = decode_refresh_token(payload.refresh_token)
    access_token = create_access_token(data={'sub': token_data.email, 'role': token_data.role})
    refresh_token = create_refresh_token(data={'sub': token_data.email, 'role': token_data.role})
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'access_token_expires_minutes': settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@router.post('/register', response_model=schemas.User)
def register_user(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')

    existing_user_count = db.query(models.User).filter(models.User.is_deleted.is_(False)).count()
    assigned_role = schemas.UserRole.admin.value if existing_user_count == 0 else user.role.value
    organisation_name = user.organisation_name or (
        f"{user.full_name}'s Security Team" if user.full_name else user.email.split('@')[0]
    )
    organisation = crud.create_organisation(db, name=organisation_name, contact_email=user.email)

    hashed_password = get_password_hash(user.password)
    created = crud.create_user(
        db=db,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=assigned_role,
        organisation_id=organisation.id,
    )
    log_audit_event(
        db,
        actor_user_id=created.id,
        actor_email=created.email,
        action='auth.register',
        entity_type='user',
        entity_id=str(created.id),
        ip_address=request.client.host if request.client else None,
        detail=f'role={assigned_role}',
    )
    return created
