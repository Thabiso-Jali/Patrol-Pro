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


@router.get('/', response_model=list[schemas.Device])
def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """List all devices with pagination."""
    return crud.get_devices(db=db, skip=skip, limit=limit, organisation_id=current_user.organisation_id)


@router.get('/{device_id}', response_model=schemas.Device)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get a specific device by ID."""
    device = crud.get_device(db=db, device_id=device_id, organisation_id=current_user.organisation_id)
    if not device:
        raise HTTPException(status_code=404, detail='Device not found')
    return device


@router.post('/', response_model=schemas.Device)
def create_device(
    device: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Create a new device."""
    created = crud.create_device(
        db=db,
        device=device,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='device.create',
        entity_type='device',
        entity_id=str(created.id),
    )
    return created


@router.put('/{device_id}', response_model=schemas.Device)
def update_device(
    device_id: int,
    device_update: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Update an existing device."""
    db_device = crud.get_device(db=db, device_id=device_id, organisation_id=current_user.organisation_id)
    if not db_device:
        raise HTTPException(status_code=404, detail='Device not found')
    updated = crud.update_device(
        db=db,
        device_id=device_id,
        device_update=device_update,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='device.update',
        entity_type='device',
        entity_id=str(device_id),
    )
    return updated


@router.delete('/{device_id}')
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Delete a device."""
    db_device = crud.get_device(db=db, device_id=device_id, organisation_id=current_user.organisation_id)
    if not db_device:
        raise HTTPException(status_code=404, detail='Device not found')
    crud.delete_device(
        db=db,
        device_id=device_id,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='device.delete',
        entity_type='device',
        entity_id=str(device_id),
    )
    return {'message': 'Device deleted successfully', 'id': device_id}
