from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine_args = {}
if SQLALCHEMY_DATABASE_URL.startswith('sqlite'):
    engine_args['connect_args'] = {'check_same_thread': False}
else:
    engine_args['pool_pre_ping'] = True

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import after Base exists to avoid model/bootstrap import cycles. The session
# event is the final security boundary even when a future endpoint omits checks.
from .services.tenant_validation import (  # noqa: E402
    enforce_tenant_and_aggregate_boundaries,
    prevent_bulk_tenant_mutation,
)

event.listen(Session, 'before_flush', enforce_tenant_and_aggregate_boundaries)
event.listen(Session, 'do_orm_execute', prevent_bulk_tenant_mutation)
