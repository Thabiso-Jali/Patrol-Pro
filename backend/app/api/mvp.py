from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import get_settings
from ..database import SessionLocal
from ..security import authenticate_user, create_access_token, create_refresh_token, get_current_user, get_password_hash
from ..services.audit import log_audit_event

router = APIRouter()
settings = get_settings()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def user_response(user) -> schemas.MVPUser:
    return schemas.MVPUser(id=user.id, name=user.full_name, email=user.email, role=user.role)


def normalize_role(role: str) -> str:
    value = role.strip().lower()
    aliases = {
        'guard': schemas.UserRole.officer.value,
        'staff': schemas.UserRole.officer.value,
        'officer': schemas.UserRole.officer.value,
        'supervisor': schemas.UserRole.supervisor.value,
        'admin': schemas.UserRole.admin.value,
    }
    if value not in aliases:
        raise HTTPException(status_code=422, detail='Unsupported role')
    return aliases[value]


@router.post('/register', response_model=schemas.MVPUser)
def register_user(request: Request, payload: schemas.MVPRegisterRequest, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, email=payload.email):
        raise HTTPException(status_code=400, detail='Email already registered')

    existing_user_count = db.query(models.User).filter(models.User.is_deleted.is_(False)).count()
    role = schemas.UserRole.admin.value if existing_user_count == 0 else normalize_role(payload.role)
    organisation = crud.create_organisation(db, name=f"{payload.name} Security", contact_email=payload.email)
    user = crud.create_user(
        db=db,
        email=payload.email,
        full_name=payload.name,
        hashed_password=get_password_hash(payload.password),
        role=role,
        organisation_id=organisation.id,
    )
    log_audit_event(
        db,
        actor_user_id=user.id,
        actor_email=user.email,
        action='auth.register',
        entity_type='user',
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    return user_response(user)


@router.post('/login', response_model=schemas.Token)
def login_user(request: Request, payload: schemas.MVPLoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.email, 'role': user.role},
        expires_delta=access_token_expires,
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


@router.get('/user', response_model=schemas.MVPUser)
def get_user(current_user=Depends(get_current_user)):
    return user_response(current_user)


@router.post('/patrol', response_model=schemas.PatrolLog)
def create_patrol_log(
    payload: schemas.PatrolLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    created = crud.create_patrol_log(
        db=db,
        patrol_log=payload,
        user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='patrol_log.create',
        entity_type='patrol_log',
        entity_id=str(created.id),
    )
    return created


@router.get('/patrol', response_model=list[schemas.PatrolLog])
def list_patrol_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return crud.get_patrol_logs(
        db=db,
        skip=skip,
        limit=limit,
        organisation_id=current_user.organisation_id,
    )


@router.post('/incidents', response_model=schemas.Incident)
def create_incident(
    payload: schemas.IncidentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    created = crud.create_incident(
        db=db,
        incident=payload,
        user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='incident.create',
        entity_type='incident',
        entity_id=str(created.id),
    )
    return created


@router.get('/incidents', response_model=list[schemas.Incident])
def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return crud.get_incidents(
        db=db,
        skip=skip,
        limit=limit,
        organisation_id=current_user.organisation_id,
    )
