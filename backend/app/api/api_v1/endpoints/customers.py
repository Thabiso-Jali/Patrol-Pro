from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from .... import crud, schemas
from ....database import SessionLocal
from ....permissions import Permission
from ....security import require_permissions
from ....services.audit import log_audit_event
from ....services.transactions import transactional_session
from ....services.concurrency import assert_expected_version, lock_tenant_record, parse_expected_version
from ....services.idempotency import execute_idempotent
from .... import models

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get('/', response_model=list[schemas.Customer])
def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.CUSTOMERS_VIEW)),
):
    """List all customers with pagination."""
    return crud.get_customers(db=db, skip=skip, limit=limit, organisation_id=current_user.organisation_id)


@router.get('/{customer_id}', response_model=schemas.Customer)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permissions(Permission.CUSTOMERS_VIEW)),
):
    """Get a specific customer by ID."""
    customer = crud.get_customer(db=db, customer_id=customer_id, organisation_id=current_user.organisation_id)
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    return customer


@router.post('/', response_model=schemas.Customer)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.CUSTOMERS_MANAGE)),
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
):
    """Create a new customer."""
    def execute():
        created = crud.create_customer(
            db=db, customer=customer, actor_user_id=current_user.id,
            organisation_id=current_user.organisation_id,
        )
        log_audit_event(
            db, actor_user_id=current_user.id, actor_email=current_user.email,
            action='customer.create', entity_type='customer', entity_id=str(created.id),
        )
        return created
    result = execute_idempotent(
        db, organisation_id=current_user.organisation_id, actor_user_id=current_user.id,
        command_type='customer.create', key=idempotency_key,
        fingerprint_payload=customer.model_dump(mode='json'), execute=execute,
        replay=lambda metadata: crud.get_customer(
            db, int(metadata['customer_id']), current_user.organisation_id,
        ), result_metadata=lambda created: {'customer_id': created.id},
    )
    created = result.value
    return created


@router.put('/{customer_id}', response_model=schemas.Customer)
def update_customer(
    customer_id: int,
    customer_update: schemas.CustomerCreate,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.CUSTOMERS_MANAGE)),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    """Update an existing customer."""
    db_customer = crud.get_customer(db=db, customer_id=customer_id, organisation_id=current_user.organisation_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    locked = lock_tenant_record(
        db, models.Customer, record_id=customer_id,
        organisation_id=current_user.organisation_id, relationship='Customer',
    )
    assert_expected_version(locked, parse_expected_version(if_match))
    updated = crud.update_customer(
        db=db,
        customer_id=customer_id,
        customer_update=customer_update,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='customer.update',
        entity_type='customer',
        entity_id=str(customer_id),
    )
    return updated


@router.delete('/{customer_id}')
def delete_customer(
    customer_id: int,
    db: Session = Depends(transactional_session),
    current_user: schemas.User = Depends(require_permissions(Permission.CUSTOMERS_MANAGE)),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    """Delete a customer."""
    db_customer = crud.get_customer(db=db, customer_id=customer_id, organisation_id=current_user.organisation_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    locked = lock_tenant_record(
        db, models.Customer, record_id=customer_id,
        organisation_id=current_user.organisation_id, relationship='Customer',
    )
    assert_expected_version(locked, parse_expected_version(if_match))
    crud.delete_customer(
        db=db,
        customer_id=customer_id,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='customer.delete',
        entity_type='customer',
        entity_id=str(customer_id),
    )
    return {'message': 'Customer deleted successfully', 'id': customer_id}
