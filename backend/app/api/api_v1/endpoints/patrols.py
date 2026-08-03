from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from .... import crud, models, schemas
from ....database import SessionLocal
from ....permissions import Permission
from ....security import require_permissions
from ....services.audit import log_audit_event
from ....services.staffing import replace_patrol_assignments, validate_schedule
from ....services.transactions import transactional_session
from ....services.patrol_occurrences import cancel_patrol_occurrence, update_patrol_occurrence
from ....services.concurrency import parse_expected_version
from ....services.idempotency import execute_idempotent

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def patrol_payload(db: Session, patrol):
    assignments = db.query(models.PatrolAssignment).filter(
        models.PatrolAssignment.patrol_id == patrol.id,
        models.PatrolAssignment.organisation_id == patrol.organisation_id,
    ).all()
    officer_ids = [row.user_id for row in assignments if row.user_id is not None]
    team_ids = [row.team_id for row in assignments if row.team_id is not None]
    names = []
    if officer_ids:
        names.extend(
            row.full_name or row.staff_identifier
            for row in db.query(models.User).filter(models.User.id.in_(officer_ids)).all()
        )
    if team_ids:
        names.extend(
            row.name
            for row in db.query(models.Team).filter(models.Team.id.in_(team_ids)).all()
        )
    return {
        **{column.name: getattr(patrol, column.name) for column in patrol.__table__.columns},
        'officer_ids': officer_ids,
        'team_ids': team_ids,
        'assignment_names': names or ([patrol.assigned_to] if patrol.assigned_to else []),
    }


@router.get('/', response_model=list[schemas.Patrol])
def list_patrols(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.PATROLS_VIEW)),
):
    """List all patrols with pagination."""
    patrols = crud.get_patrols(
        db=db, skip=skip, limit=limit, organisation_id=current_user.organisation_id,
    )
    return [patrol_payload(db, patrol) for patrol in patrols]


@router.get('/{patrol_id}', response_model=schemas.Patrol)
def get_patrol(
    patrol_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.PATROLS_VIEW)),
):
    """Get a specific patrol by ID."""
    patrol = crud.get_patrol(db=db, patrol_id=patrol_id, organisation_id=current_user.organisation_id)
    if not patrol:
        raise HTTPException(status_code=404, detail='Patrol not found')
    return patrol_payload(db, patrol)


@router.post('/', response_model=schemas.Patrol)
def create_patrol(
    patrol: schemas.PatrolCreate,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.PATROLS_MANAGE)),
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
):
    """Create a new patrol."""
    validate_schedule(patrol.start_time, patrol.end_time)
    def execute():
        created = crud.create_patrol(
            db=db, patrol=patrol, actor_user_id=current_user.id,
            organisation_id=current_user.organisation_id,
        )
        replace_patrol_assignments(db, created, patrol.officer_ids, patrol.team_ids, current_user.id)
        log_audit_event(
            db, actor_user_id=current_user.id, actor_email=current_user.email,
            action='patrol.create', entity_type='patrol', entity_id=str(created.id),
            organisation_id=current_user.organisation_id,
        )
        return created
    result = execute_idempotent(
        db, organisation_id=current_user.organisation_id, actor_user_id=current_user.id,
        command_type='patrol.create', key=idempotency_key,
        fingerprint_payload=patrol.model_dump(mode='json'), execute=execute,
        replay=lambda metadata: crud.get_patrol(
            db, int(metadata['patrol_id']), current_user.organisation_id,
        ),
        result_metadata=lambda created: {'patrol_id': created.id},
    )
    created = result.value
    return patrol_payload(db, created)


@router.put('/{patrol_id}', response_model=schemas.Patrol)
def update_patrol(
    patrol_id: int,
    patrol_update: schemas.PatrolCreate,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.PATROLS_MANAGE)),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    """Update an existing patrol."""
    db_patrol = crud.get_patrol(db=db, patrol_id=patrol_id, organisation_id=current_user.organisation_id)
    if not db_patrol:
        raise HTTPException(status_code=404, detail='Patrol not found')
    validate_schedule(patrol_update.start_time, patrol_update.end_time)
    updated = update_patrol_occurrence(
        db=db,
        patrol_id=patrol_id,
        payload=patrol_update,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
        expected_version=parse_expected_version(if_match),
    )
    replace_patrol_assignments(
        db,
        updated,
        patrol_update.officer_ids,
        patrol_update.team_ids,
        current_user.id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='patrol.update',
        entity_type='patrol',
        entity_id=str(patrol_id),
        organisation_id=current_user.organisation_id,
    )
    return patrol_payload(db, updated)


@router.delete('/{patrol_id}')
def delete_patrol(
    patrol_id: int,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.PATROLS_MANAGE)),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    """Delete a patrol."""
    db_patrol = crud.get_patrol(db=db, patrol_id=patrol_id, organisation_id=current_user.organisation_id)
    if not db_patrol:
        raise HTTPException(status_code=404, detail='Patrol not found')
    cancel_patrol_occurrence(
        db=db,
        patrol_id=patrol_id,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
        expected_version=parse_expected_version(if_match),
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
