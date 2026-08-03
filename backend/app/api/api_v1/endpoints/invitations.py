import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .... import crud, models, schemas
from ....config import get_settings
from ....database import SessionLocal
from ....permissions import Permission, canonical_role
from ....security import get_password_hash, require_permissions
from ....services.audit import log_audit_event
from ....services.transactions import transactional_session
from ....services.idempotency import execute_idempotent

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
    db: Session = Depends(transactional_session),
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
    )
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
    db: Session = Depends(transactional_session),
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
):
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    invitation = db.query(models.EmployeeInvitation).filter(
        models.EmployeeInvitation.token_hash == token_hash,
    ).with_for_update().first()
    expiry = invitation.expires_at if invitation else None
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if invitation is None or expiry <= now:
        raise HTTPException(status_code=400, detail='Invitation is invalid or expired')
    if invitation.accepted_at is not None and idempotency_key is None:
        raise HTTPException(status_code=400, detail='Invitation is invalid or expired')
    existing_user = crud.get_user_by_email(db, invitation.email)
    if existing_user and idempotency_key is None:
        raise HTTPException(status_code=409, detail='Email is already registered')

    def execute():
        if invitation.accepted_at is not None or existing_user:
            raise HTTPException(status_code=409, detail='Invitation has already been accepted')
        user = crud.create_user(
            db, email=invitation.email, full_name=invitation.full_name,
            hashed_password=get_password_hash(payload.password), role=invitation.role,
            organisation_id=invitation.organisation_id, created_by=invitation.invited_by,
        )
        invitation.accepted_at = now
        log_audit_event(
            db, actor_user_id=user.id, actor_email=user.email,
            organisation_id=user.organisation_id, action='user.invitation.accept',
            entity_type='user', entity_id=str(user.id),
            ip_address=request.client.host if request.client else None,
        )
        return user

    result = execute_idempotent(
        db, organisation_id=invitation.organisation_id, actor_user_id=None,
        actor_scope=f'invitation:{invitation.id}', command_type='invitation.accept',
        key=idempotency_key,
        fingerprint_payload={
            'invitation_id': invitation.id,
            'password_fingerprint': hashlib.sha256(payload.password.encode()).hexdigest(),
        }, execute=execute,
        replay=lambda metadata: db.query(models.User).filter(
            models.User.id == int(metadata['user_id']),
            models.User.organisation_id == invitation.organisation_id,
        ).one(), result_metadata=lambda user: {'user_id': user.id},
    )
    return result.value
