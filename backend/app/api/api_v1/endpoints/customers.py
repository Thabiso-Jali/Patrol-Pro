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


@router.get('/', response_model=list[schemas.Customer])
def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """List all customers with pagination."""
    return crud.get_customers(db=db, skip=skip, limit=limit, organisation_id=current_user.organisation_id)


@router.get('/{customer_id}', response_model=schemas.Customer)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get a specific customer by ID."""
    customer = crud.get_customer(db=db, customer_id=customer_id, organisation_id=current_user.organisation_id)
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    return customer


@router.post('/', response_model=schemas.Customer)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Create a new customer."""
    created = crud.create_customer(
        db=db,
        customer=customer,
        actor_user_id=current_user.id,
        organisation_id=current_user.organisation_id,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        action='customer.create',
        entity_type='customer',
        entity_id=str(created.id),
    )
    return created


@router.put('/{customer_id}', response_model=schemas.Customer)
def update_customer(
    customer_id: int,
    customer_update: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Update an existing customer."""
    db_customer = crud.get_customer(db=db, customer_id=customer_id, organisation_id=current_user.organisation_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail='Customer not found')
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
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_roles(schemas.UserRole.admin, schemas.UserRole.supervisor)),
):
    """Delete a customer."""
    db_customer = crud.get_customer(db=db, customer_id=customer_id, organisation_id=current_user.organisation_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail='Customer not found')
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
