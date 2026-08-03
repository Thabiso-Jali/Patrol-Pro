from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from .... import crud, schemas
from ....database import SessionLocal
from ....domain.states import validate_state_change
from ....permissions import Permission
from ....security import require_permissions
from ....services.audit import log_audit_event
from ....services.transactions import transactional_session
from ....services import incidents as incident_service
from ....services.concurrency import parse_expected_version
from ....services.idempotency import execute_idempotent

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
    current_user: schemas.User = Depends(require_permissions(Permission.INCIDENTS_VIEW)),
):
    """List all alerts with pagination."""
    return crud.get_alerts(db=db, skip=skip, limit=limit, organisation_id=current_user.organisation_id)


@router.get('/{alert_id}', response_model=schemas.Alert)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.INCIDENTS_VIEW)),
):
    """Get a specific alert by ID."""
    alert = crud.get_alert(db=db, alert_id=alert_id, organisation_id=current_user.organisation_id)
    if not alert:
        raise HTTPException(status_code=404, detail='Alert not found')
    return alert


@router.post('/', response_model=schemas.Alert)
def create_alert(
    alert: schemas.AlertCreate,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.INCIDENTS_CREATE)),
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
):
    """Create a new alert."""
    validate_alert_references(db, alert, current_user.organisation_id)
    def execute():
        created = incident_service.create_incident(
            db=db, payload=alert, actor_user_id=current_user.id,
            organisation_id=current_user.organisation_id,
        )
        crud.create_notification(
            db=db,
            notification=schemas.NotificationCreate(
                title=f'Incident reported: {created.title}', body=created.description,
                category='incident', priority=created.severity,
            ), actor_user_id=current_user.id, organisation_id=current_user.organisation_id,
        )
        log_audit_event(
            db, actor_user_id=current_user.id, actor_email=current_user.email,
            action='alert.create', entity_type='incident', entity_id=str(created.id),
        )
        return created
    result = execute_idempotent(
        db, organisation_id=current_user.organisation_id, actor_user_id=current_user.id,
        command_type='incident.create', key=idempotency_key,
        fingerprint_payload=alert.model_dump(mode='json'), execute=execute,
        replay=lambda metadata: crud.get_alert(
            db, int(metadata['incident_id']), current_user.organisation_id,
        ), result_metadata=lambda created: {'incident_id': created.id},
    )
    created = result.value
    return created


@router.put('/{alert_id}', response_model=schemas.Alert)
def update_alert(
    alert_id: int,
    alert_update: schemas.AlertCreate,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.INCIDENTS_MANAGE)),
    if_match: str | None = Header(default=None, alias='If-Match'),
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
):
    """Update an existing alert."""
    expected_version = parse_expected_version(if_match)

    def execute():
        db_alert = crud.get_alert(db=db, alert_id=alert_id, organisation_id=current_user.organisation_id)
        if not db_alert:
            raise HTTPException(status_code=404, detail='Alert not found')
        provided_fields = frozenset(
            field for field, value in {'resolution_notes': alert_update.resolution_notes}.items()
            if value and value.strip()
        )
        validate_state_change(
            'incident', db_alert.status, alert_update.status.value,
            provided_fields=provided_fields,
        )
        validate_alert_references(db, alert_update, current_user.organisation_id)
        updated = incident_service.update_incident(
            db=db, incident_id=alert_id, payload=alert_update,
            actor_user_id=current_user.id, organisation_id=current_user.organisation_id,
            expected_version=expected_version,
        )
        log_audit_event(
            db, actor_user_id=current_user.id, actor_email=current_user.email,
            action='alert.update', entity_type='incident', entity_id=str(alert_id),
        )
        return updated

    result = execute_idempotent(
        db, organisation_id=current_user.organisation_id, actor_user_id=current_user.id,
        command_type='incident.update', key=idempotency_key,
        fingerprint_payload={
            'incident_id': alert_id, 'expected_version': expected_version,
            'payload': alert_update.model_dump(mode='json'),
        }, execute=execute,
        replay=lambda metadata: crud.get_alert(
            db, int(metadata['incident_id']), current_user.organisation_id,
        ), result_metadata=lambda updated: {
            'incident_id': updated.id, 'status': updated.status,
            'record_version': updated.record_version,
        },
    )
    return result.value


@router.delete('/{alert_id}')
def delete_alert(
    alert_id: int,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.INCIDENTS_MANAGE)),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    """Delete an alert."""
    db_alert = crud.get_alert(db=db, alert_id=alert_id, organisation_id=current_user.organisation_id)
    if not db_alert:
        raise HTTPException(status_code=404, detail='Alert not found')
    incident_service.archive_incident(
        db=db,
        incident_id=alert_id,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
        expected_version=parse_expected_version(if_match),
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='alert.delete',
        entity_type='incident',
        entity_id=str(alert_id),
    )
    return {'message': 'Alert deleted successfully', 'id': alert_id}
