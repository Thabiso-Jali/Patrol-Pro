from datetime import datetime

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


@router.get('/', response_model=list[schemas.Patrol])
def list_patrols(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """List all patrols with pagination."""
    return crud.get_patrols(db=db, skip=skip, limit=limit, organisation_id=current_user.organisation_id)


@router.get('/{patrol_id}', response_model=schemas.Patrol)
def get_patrol(
    patrol_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get a specific patrol by ID."""
    patrol = crud.get_patrol(db=db, patrol_id=patrol_id, organisation_id=current_user.organisation_id)
    if not patrol:
        raise HTTPException(status_code=404, detail='Patrol not found')
    return patrol


@router.post('/', response_model=schemas.Patrol)
def create_patrol(
    patrol: schemas.PatrolCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Create a new patrol."""
    created = crud.create_patrol(
        db=db,
        patrol=patrol,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='patrol.create',
        entity_type='patrol',
        entity_id=str(created.id),
    )
    return created


@router.put('/{patrol_id}', response_model=schemas.Patrol)
def update_patrol(
    patrol_id: int,
    patrol_update: schemas.PatrolCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Update an existing patrol."""
    db_patrol = crud.get_patrol(db=db, patrol_id=patrol_id, organisation_id=current_user.organisation_id)
    if not db_patrol:
        raise HTTPException(status_code=404, detail='Patrol not found')
    updated = crud.update_patrol(
        db=db,
        patrol_id=patrol_id,
        patrol_update=patrol_update,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='patrol.update',
        entity_type='patrol',
        entity_id=str(patrol_id),
    )
    return updated


@router.delete('/{patrol_id}')
def delete_patrol(
    patrol_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Delete a patrol."""
    db_patrol = crud.get_patrol(db=db, patrol_id=patrol_id, organisation_id=current_user.organisation_id)
    if not db_patrol:
        raise HTTPException(status_code=404, detail='Patrol not found')
    crud.delete_patrol(
        db=db,
        patrol_id=patrol_id,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='patrol.delete',
        entity_type='patrol',
        entity_id=str(patrol_id),
    )
    return {'message': 'Patrol deleted successfully', 'id': patrol_id}
