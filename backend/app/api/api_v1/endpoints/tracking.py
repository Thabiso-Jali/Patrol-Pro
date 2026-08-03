from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .... import crud, schemas
from ....database import SessionLocal
from ....permissions import Permission
from ....security import require_permissions
from ....services.audit import log_audit_event
from ....services.transactions import transactional_session

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
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.OPERATIONS_WRITE)),
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
    current_user: schemas.User = Depends(require_permissions(Permission.TRACKING_VIEW)),
):
    return crud.get_latest_officer_locations(
        db=db,
        organisation_id=current_user.organisation_id,
        limit=limit,
    )
