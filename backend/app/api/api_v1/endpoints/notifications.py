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


@router.get('/', response_model=list[schemas.Notification])
def list_notifications(
    unread_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    return crud.get_notifications(
        db=db,
        user_id=current_user.id,
        organisation_id=current_user.organisation_id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )


@router.post('/', response_model=schemas.Notification)
def create_notification(
    notification: schemas.NotificationCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    created = crud.create_notification(
        db=db,
        notification=notification,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='notification.create',
        entity_type='notification',
        entity_id=str(created.id),
    )
    return created


@router.post('/{notification_id}/read', response_model=schemas.Notification)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    notification = crud.mark_notification_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    if not notification:
        raise HTTPException(status_code=404, detail='Notification not found')
    return notification
