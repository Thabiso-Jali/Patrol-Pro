from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .... import crud, models, schemas
from ....database import SessionLocal
from ....permissions import Permission
from ....security import require_permissions
from ....services.audit import log_audit_event
from ....services.employees import employee_for_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_patrol(db: Session, patrol_id: int | None, organisation_id: int | None):
    if patrol_id and not crud.get_patrol(db, patrol_id, organisation_id):
        raise HTTPException(status_code=400, detail='Patrol does not exist for this organisation')


def validate_code(
    db: Session,
    code: str,
    organisation_id: int,
    exclude_checkpoint_id: int | None = None,
):
    query = db.query(models.Checkpoint).filter(
        models.Checkpoint.organisation_id == organisation_id,
        models.Checkpoint.code == code,
        models.Checkpoint.is_deleted.is_(False),
    )
    if exclude_checkpoint_id is not None:
        query = query.filter(models.Checkpoint.id != exclude_checkpoint_id)
    if query.first():
        raise HTTPException(status_code=409, detail='Checkpoint code already exists')


@router.get('/', response_model=list[schemas.Checkpoint])
def list_checkpoints(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.CHECKPOINTS_VIEW)),
):
    return crud.get_checkpoints(
        db=db,
        skip=skip,
        limit=limit,
        organisation_id=current_user.organisation_id,
    )


@router.post('/', response_model=schemas.Checkpoint)
def create_checkpoint(
    checkpoint: schemas.CheckpointCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.CHECKPOINTS_MANAGE)),
):
    validate_patrol(db, checkpoint.patrol_id, current_user.organisation_id)
    validate_code(db, checkpoint.code, current_user.organisation_id)
    if checkpoint.status == 'verified':
        raise HTTPException(status_code=422, detail='Checkpoint codes can only be accepted through code confirmation')
    created = crud.create_checkpoint(
        db=db,
        checkpoint=checkpoint,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='checkpoint.create',
        entity_type='checkpoint',
        entity_id=str(created.id),
    )
    return created


@router.put('/{checkpoint_id}', response_model=schemas.Checkpoint)
def update_checkpoint(
    checkpoint_id: int,
    payload: schemas.CheckpointCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.CHECKPOINTS_MANAGE)),
):
    checkpoint = crud.get_checkpoint(db, checkpoint_id, current_user.organisation_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail='Checkpoint not found')
    if checkpoint.status == 'verified':
        raise HTTPException(status_code=409, detail='Code-confirmed checkpoints cannot be edited')
    if payload.status == 'verified':
        raise HTTPException(status_code=422, detail='Use code confirmation to accept a checkpoint code')
    validate_patrol(db, payload.patrol_id, current_user.organisation_id)
    validate_code(db, payload.code, current_user.organisation_id, checkpoint_id)
    updated = crud.update_checkpoint(
        db,
        checkpoint_id,
        payload,
        current_user.id,
        current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        organisation_id=current_user.organisation_id,
        action='checkpoint.update',
        entity_type='checkpoint',
        entity_id=str(checkpoint_id),
    )
    return updated


@router.delete('/{checkpoint_id}', status_code=204)
def archive_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.CHECKPOINTS_MANAGE)),
):
    checkpoint = crud.get_checkpoint(db, checkpoint_id, current_user.organisation_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail='Checkpoint not found')
    if checkpoint.status == 'verified':
        raise HTTPException(status_code=409, detail='Code-confirmed checkpoints must be retained for audit')
    crud.delete_checkpoint(db, checkpoint_id, current_user.id, current_user.organisation_id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        organisation_id=current_user.organisation_id,
        action='checkpoint.archive',
        entity_type='checkpoint',
        entity_id=str(checkpoint_id),
    )
    return None


@router.post('/{checkpoint_id}/verify', response_model=schemas.Checkpoint)
def verify_checkpoint(
    checkpoint_id: int,
    payload: schemas.CheckpointVerify,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.CHECKPOINTS_VERIFY)),
):
    checkpoint = crud.get_checkpoint(db, checkpoint_id, current_user.organisation_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail='Checkpoint not found')
    if checkpoint.status == 'verified':
        raise HTTPException(status_code=409, detail='Checkpoint code has already been accepted')
    if checkpoint.status == 'inactive':
        raise HTTPException(status_code=409, detail='Inactive checkpoints cannot accept a code')
    if payload.code and payload.code != checkpoint.code:
        raise HTTPException(status_code=400, detail='Checkpoint code does not match')
    if payload.nfc_tag and checkpoint.nfc_tag and payload.nfc_tag != checkpoint.nfc_tag:
        raise HTTPException(status_code=400, detail='NFC tag does not match')

    verified = crud.verify_checkpoint(
        db=db,
        checkpoint_id=checkpoint_id,
        payload=payload,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
        commit=False,
    )
    employee = employee_for_user(
        db,
        organisation_id=current_user.organisation_id,
        user_id=current_user.id,
    )
    if employee is None:
        raise HTTPException(status_code=409, detail='Operational employee profile is unavailable')
    db.add(models.CheckpointVerificationEvent(
        organisation_id=current_user.organisation_id,
        checkpoint_id=checkpoint.id,
        patrol_occurrence_id=checkpoint.patrol_id,
        employee_id=employee.id,
        occurred_at=verified.verified_at,
        verification_method='nfc' if payload.nfc_tag else 'code',
        result='accepted',
        latitude=payload.latitude,
        longitude=payload.longitude,
    ))
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='checkpoint.verify',
        entity_type='checkpoint',
        entity_id=str(checkpoint_id),
    )
    return verified
