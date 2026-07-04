from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .... import crud, schemas
from ....database import SessionLocal
from ....security import get_current_user, require_roles
from ....services.audit import log_audit_event

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


@router.get('/', response_model=list[schemas.Checkpoint])
def list_checkpoints(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
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
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    validate_patrol(db, checkpoint.patrol_id, current_user.organisation_id)
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


@router.post('/{checkpoint_id}/verify', response_model=schemas.Checkpoint)
def verify_checkpoint(
    checkpoint_id: int,
    payload: schemas.CheckpointVerify,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    checkpoint = crud.get_checkpoint(db, checkpoint_id, current_user.organisation_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail='Checkpoint not found')
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
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='checkpoint.verify',
        entity_type='checkpoint',
        entity_id=str(checkpoint_id),
    )
    return verified
