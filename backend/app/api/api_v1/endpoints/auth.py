from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
import hashlib
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
    get_current_user,
    get_password_hash,
)
from ....services.audit import log_audit_event
from ....services.transactions import transactional, transactional_session
from ....permissions import canonical_role, permission_values_for_role
from ....services.idempotency import execute_idempotent, normalize_key

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
    with transactional(db, owner='auth.login'):
        user = authenticate_user(db, form_data.username, form_data.password)
        if user:
            company = db.query(models.Organisation).filter(
                models.Organisation.id == user.organisation_id,
            ).one()
            log_audit_event(
                db,
                actor_user_id=user.id,
                actor_email=user.email,
                organisation_id=user.organisation_id,
                action='auth.login',
                entity_type='user',
                entity_id=str(user.id),
                ip_address=request.client.host if request.client else None,
            )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user, company, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(user, company)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'access_token_expires_minutes': settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@router.post('/refresh', response_model=schemas.Token)
def refresh_access_token(payload: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    token_data = decode_refresh_token(payload.refresh_token)
    user = db.query(models.User).filter(
        models.User.id == token_data.user_id,
        models.User.organisation_id == token_data.company_id,
        models.User.is_active.is_(True),
        models.User.is_deleted.is_(False),
    ).first()
    company = db.query(models.Organisation).filter(
        models.Organisation.id == token_data.company_id,
        models.Organisation.is_active.is_(True),
        models.Organisation.status == 'active',
    ).first()
    if (
        user is None
        or company is None
        or user.session_version != token_data.session_version
        or max(user.permission_version, company.permission_version) != token_data.permission_version
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')
    access_token = create_access_token(user, company)
    refresh_token = create_refresh_token(user, company)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'access_token_expires_minutes': settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@router.post('/register', response_model=schemas.RegistrationResult)
def register_company(
    request: Request,
    registration: schemas.CompanyRegistration,
    db: Session = Depends(transactional_session),
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
):
    normalized_key = normalize_key(idempotency_key)
    db_user = crud.get_user_by_email(db, email=registration.owner_email)
    if db_user and normalized_key is None:
        raise HTTPException(status_code=400, detail='Email already registered')
    try:
        ZoneInfo(registration.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail='Unknown company timezone') from exc
    if db_user:
        organisation = db.query(models.Organisation).filter(
            models.Organisation.id == db_user.organisation_id,
        ).one()
    else:
        organisation = crud.create_organisation(
            db, name=registration.company_name,
            contact_email=str(registration.business_email), business_email=str(registration.business_email),
            registration_number=registration.registration_number, vat_number=registration.vat_number,
            tax_number=registration.tax_number, address=registration.address,
            country=registration.country, timezone=registration.timezone,
            industry=registration.industry, phone=registration.phone,
            subscription_plan=registration.subscription_plan,
        )

    def execute():
        owner = crud.create_user(
            db=db, email=str(registration.owner_email), full_name=registration.owner_name,
            hashed_password=get_password_hash(registration.password),
            role=schemas.UserRole.company_owner.value, organisation_id=organisation.id,
        )
        log_audit_event(
            db, actor_user_id=owner.id, actor_email=owner.email,
            organisation_id=organisation.id, action='company.register',
            entity_type='organisation', entity_id=str(organisation.id),
            ip_address=request.client.host if request.client else None,
            detail='company owner created',
        )
        return {'company': organisation, 'owner': owner}

    result = execute_idempotent(
        db, organisation_id=organisation.id, actor_user_id=None,
        actor_scope='registration:' + hashlib.sha256(str(registration.owner_email).lower().encode()).hexdigest(),
        command_type='organisation.register', key=normalized_key,
        fingerprint_payload={
            **registration.model_dump(mode='json', exclude={'password'}),
            'password_fingerprint': hashlib.sha256(registration.password.encode()).hexdigest(),
        }, execute=execute,
        replay=lambda metadata: {
            'company': db.query(models.Organisation).filter_by(id=int(metadata['organisation_id'])).one(),
            'owner': db.query(models.User).filter_by(
                id=int(metadata['owner_id']), organisation_id=organisation.id,
            ).one(),
        },
        result_metadata=lambda value: {
            'organisation_id': value['company'].id, 'owner_id': value['owner'].id,
        },
    )
    return result.value


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(transactional_session),
):
    user = db.query(models.User).filter(
        models.User.id == current_user.id,
        models.User.organisation_id == current_user.organisation_id,
    ).one()
    user.session_version += 1
    log_audit_event(
        db,
        actor_user_id=user.id,
        actor_email=user.email,
        organisation_id=user.organisation_id,
        action='auth.logout',
        entity_type='user',
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )


@router.get('/me', response_model=schemas.AuthContext)
def authentication_context(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = db.query(models.Organisation).filter(
        models.Organisation.id == current_user.organisation_id,
        models.Organisation.is_active.is_(True),
    ).one()
    return {
        'user': current_user,
        'company': company,
        'role': canonical_role(current_user.role),
        'permissions': permission_values_for_role(current_user.role),
    }
