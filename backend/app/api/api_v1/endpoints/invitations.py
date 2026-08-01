import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .... import crud, models, schemas
from ....config import get_settings
from ....database import SessionLocal
from ....permissions import Permission, canonical_role
from ....security import get_password_hash, require_permissions
from ....services.audit import log_audit_event

router = APIRouter()
settings = get_settings()
INVITABLE_ROLES = {'administrator', 'manager', 'supervisor', 'officer', 'employee', 'read_only'}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    '',
    response_model=schemas.EmployeeInvitationCreated,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def invite_employee(
    request: Request,
    payload: schemas.EmployeeInvitationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permissions(Permission.USERS_INVITE)),
):
    role = canonical_role(payload.role.value)
    if role not in INVITABLE_ROLES:
        raise HTTPException(status_code=422, detail='Role cannot be assigned by invitation')
    if crud.get_user_by_email(db, str(payload.email)):
        raise HTTPException(status_code=409, detail='Email is already registered')
    now = datetime.now(timezone.utc)
    existing = db.query(models.EmployeeInvitation).filter(
        models.EmployeeInvitation.organisation_id == current_user.organisation_id,
        models.EmployeeInvitation.email == str(payload.email),
        models.EmployeeInvitation.accepted_at.is_(None),
        models.EmployeeInvitation.expires_at > now,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail='An active invitation already exists')
    raw_token = secrets.token_urlsafe(32)
    invitation = models.EmployeeInvitation(
        organisation_id=current_user.organisation_id,
        email=str(payload.email),
        full_name=payload.full_name,
        role=role,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=now + timedelta(hours=settings.EMPLOYEE_INVITATION_EXPIRE_HOURS),
        invited_by=current_user.id,
    )
    db.add(invitation)
    db.flush()
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        organisation_id=current_user.organisation_id,
        action='user.invite',
        entity_type='employee_invitation',
        entity_id=str(invitation.id),
        ip_address=request.client.host if request.client else None,
        detail=f'role={role}',
        commit=False,
    )
    db.commit()
    db.refresh(invitation)
    response = {
        'id': invitation.id,
        'email': invitation.email,
        'full_name': invitation.full_name,
        'role': invitation.role,
        'expires_at': invitation.expires_at,
    }
    if settings.expose_invitation_tokens:
        response['invitation_token'] = raw_token
    return response


@router.post('/accept', response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def accept_invitation(
    request: Request,
    payload: schemas.EmployeeInvitationAccept,
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    invitation = db.query(models.EmployeeInvitation).filter(
        models.EmployeeInvitation.token_hash == token_hash,
        models.EmployeeInvitation.accepted_at.is_(None),
    ).first()
    expiry = invitation.expires_at if invitation else None
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if invitation is None or expiry <= now:
        raise HTTPException(status_code=400, detail='Invitation is invalid or expired')
    if crud.get_user_by_email(db, invitation.email):
        raise HTTPException(status_code=409, detail='Email is already registered')
    try:
        user = crud.create_user(
            db,
            email=invitation.email,
            full_name=invitation.full_name,
            hashed_password=get_password_hash(payload.password),
            role=invitation.role,
            organisation_id=invitation.organisation_id,
            created_by=invitation.invited_by,
            commit=False,
        )
        invitation.accepted_at = now
        log_audit_event(
            db,
            actor_user_id=user.id,
            actor_email=user.email,
            organisation_id=user.organisation_id,
            action='user.invitation.accept',
            entity_type='user',
            entity_id=str(user.id),
            ip_address=request.client.host if request.client else None,
            commit=False,
        )
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user
