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


@router.post('/locations', response_model=schemas.OfficerLocation)
def create_location_ping(
    location: schemas.OfficerLocationCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if location.patrol_id and not crud.get_patrol(db, location.patrol_id, current_user.organisation_id):
        raise HTTPException(status_code=400, detail='Patrol does not exist for this organisation')
    created = crud.create_officer_location(
        db=db,
        location=location,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='tracking.location_ping',
        entity_type='officer_location',
        entity_id=str(created.id),
    )
    return created


@router.get('/locations/latest', response_model=list[schemas.OfficerLocation])
def list_latest_locations(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    return crud.get_latest_officer_locations(
        db=db,
        organisation_id=current_user.organisation_id,
        limit=limit,
    )
