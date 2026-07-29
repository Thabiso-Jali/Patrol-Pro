from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .... import crud, schemas
from ....database import SessionLocal
from ....permissions import Permission
from ....security import require_permissions
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
    current_user: schemas.User = Depends(require_permissions(Permission.DEVICES_VIEW)),
):
    """List all devices with pagination."""
    return crud.get_devices(db=db, skip=skip, limit=limit, organisation_id=current_user.organisation_id)


@router.get('/{device_id}', response_model=schemas.Device)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.DEVICES_VIEW)),
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
    current_user: schemas.User = Depends(require_permissions(Permission.DEVICES_MANAGE)),
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
    current_user: schemas.User = Depends(require_permissions(Permission.DEVICES_MANAGE)),
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
    current_user: schemas.User = Depends(require_permissions(Permission.DEVICES_MANAGE)),
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
