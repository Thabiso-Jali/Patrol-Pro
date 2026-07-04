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


def validate_alert_references(db: Session, alert: schemas.AlertCreate, organisation_id: int | None):
    if alert.patrol_id and not crud.get_patrol(db, alert.patrol_id, organisation_id):
        raise HTTPException(status_code=400, detail='Patrol does not exist for this organisation')
    if alert.device_id and not crud.get_device(db, alert.device_id, organisation_id):
        raise HTTPException(status_code=400, detail='Device does not exist for this organisation')
    if alert.customer_id and not crud.get_customer(db, alert.customer_id, organisation_id):
        raise HTTPException(status_code=400, detail='Customer does not exist for this organisation')


@router.get('/', response_model=list[schemas.Alert])
def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """List all alerts with pagination."""
    return crud.get_alerts(db=db, skip=skip, limit=limit, organisation_id=current_user.organisation_id)


@router.get('/{alert_id}', response_model=schemas.Alert)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get a specific alert by ID."""
    alert = crud.get_alert(db=db, alert_id=alert_id, organisation_id=current_user.organisation_id)
    if not alert:
        raise HTTPException(status_code=404, detail='Alert not found')
    return alert


@router.post('/', response_model=schemas.Alert)
def create_alert(
    alert: schemas.AlertCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Create a new alert."""
    validate_alert_references(db, alert, current_user.organisation_id)
    created = crud.create_alert(
        db=db,
        alert=alert,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    crud.create_notification(
        db=db,
        notification=schemas.NotificationCreate(
            title=f'Incident reported: {created.title}',
            body=created.description,
            category='incident',
            priority=created.severity,
        ),
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='alert.create',
        entity_type='alert',
        entity_id=str(created.id),
    )
    return created


@router.put('/{alert_id}', response_model=schemas.Alert)
def update_alert(
    alert_id: int,
    alert_update: schemas.AlertCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Update an existing alert."""
    db_alert = crud.get_alert(db=db, alert_id=alert_id, organisation_id=current_user.organisation_id)
    if not db_alert:
        raise HTTPException(status_code=404, detail='Alert not found')
    validate_alert_references(db, alert_update, current_user.organisation_id)
    updated = crud.update_alert(
        db=db,
        alert_id=alert_id,
        alert_update=alert_update,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='alert.update',
        entity_type='alert',
        entity_id=str(alert_id),
    )
    return updated


@router.delete('/{alert_id}')
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Delete an alert."""
    db_alert = crud.get_alert(db=db, alert_id=alert_id, organisation_id=current_user.organisation_id)
    if not db_alert:
        raise HTTPException(status_code=404, detail='Alert not found')
    crud.delete_alert(
        db=db,
        alert_id=alert_id,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='alert.delete',
        entity_type='alert',
        entity_id=str(alert_id),
    )
    return {'message': 'Alert deleted successfully', 'id': alert_id}
