import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .config import get_settings
from .database import engine, Base
from .middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
from .api.api_v1.api import api_router
from .api.mvp import router as mvp_router

# Get settings before configuring process-wide behavior
settings = get_settings()

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
logger.info("CORS configured for %d origin(s)", len(settings.ALLOWED_ORIGINS))


def initialize_development_database() -> None:
    """Backfill newly introduced columns for local SQLite deployments.

    Demo and production schemas must be managed exclusively with Alembic.
    """
    if settings.APP_ENV != "development" or not settings.DATABASE_URL.startswith("sqlite"):
        return

    Base.metadata.create_all(bind=engine)
    logger.info("Local SQLite development database initialized")

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    migration_map = {
        'organisations': [
            'ALTER TABLE organisations ADD COLUMN business_email VARCHAR',
            'ALTER TABLE organisations ADD COLUMN registration_number VARCHAR',
            'ALTER TABLE organisations ADD COLUMN vat_number VARCHAR',
            'ALTER TABLE organisations ADD COLUMN tax_number VARCHAR',
            'ALTER TABLE organisations ADD COLUMN address TEXT',
            'ALTER TABLE organisations ADD COLUMN country VARCHAR',
            "ALTER TABLE organisations ADD COLUMN timezone VARCHAR DEFAULT 'UTC'",
            'ALTER TABLE organisations ADD COLUMN industry VARCHAR',
            'ALTER TABLE organisations ADD COLUMN phone VARCHAR',
            "ALTER TABLE organisations ADD COLUMN subscription_plan VARCHAR DEFAULT 'pilot'",
            'ALTER TABLE organisations ADD COLUMN permission_version INTEGER DEFAULT 1',
            "ALTER TABLE organisations ADD COLUMN status VARCHAR DEFAULT 'active'",
        ],
        'users': [
            "ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'officer'",
            'ALTER TABLE users ADD COLUMN role_migrated_from_admin BOOLEAN DEFAULT 0',
            "ALTER TABLE users ADD COLUMN created_at DATETIME",
            "ALTER TABLE users ADD COLUMN updated_at DATETIME",
            "ALTER TABLE users ADD COLUMN created_by INTEGER",
            "ALTER TABLE users ADD COLUMN updated_by INTEGER",
            "ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN organisation_id INTEGER",
            'ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1',
            'ALTER TABLE users ADD COLUMN session_version INTEGER DEFAULT 1',
            'ALTER TABLE users ADD COLUMN permission_version INTEGER DEFAULT 1',
            'ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0',
            'ALTER TABLE users ADD COLUMN locked_until DATETIME',
            'ALTER TABLE users ADD COLUMN last_login_at DATETIME',
        ],
        'patrols': [
            'ALTER TABLE patrols ADD COLUMN created_at DATETIME',
            'ALTER TABLE patrols ADD COLUMN updated_at DATETIME',
            'ALTER TABLE patrols ADD COLUMN created_by INTEGER',
            'ALTER TABLE patrols ADD COLUMN updated_by INTEGER',
            'ALTER TABLE patrols ADD COLUMN is_deleted BOOLEAN DEFAULT 0',
            'ALTER TABLE patrols ADD COLUMN organisation_id INTEGER',
        ],
        'patrol_logs': [
            'ALTER TABLE patrol_logs ADD COLUMN organisation_id INTEGER',
        ],
        'incidents': [
            'ALTER TABLE incidents ADD COLUMN organisation_id INTEGER',
        ],
        'devices': [
            'ALTER TABLE devices ADD COLUMN created_at DATETIME',
            'ALTER TABLE devices ADD COLUMN updated_at DATETIME',
            'ALTER TABLE devices ADD COLUMN created_by INTEGER',
            'ALTER TABLE devices ADD COLUMN updated_by INTEGER',
            'ALTER TABLE devices ADD COLUMN is_deleted BOOLEAN DEFAULT 0',
            'ALTER TABLE devices ADD COLUMN organisation_id INTEGER',
        ],
        'customers': [
            'ALTER TABLE customers ADD COLUMN created_at DATETIME',
            'ALTER TABLE customers ADD COLUMN updated_at DATETIME',
            'ALTER TABLE customers ADD COLUMN created_by INTEGER',
            'ALTER TABLE customers ADD COLUMN updated_by INTEGER',
            'ALTER TABLE customers ADD COLUMN is_deleted BOOLEAN DEFAULT 0',
            'ALTER TABLE customers ADD COLUMN organisation_id INTEGER',
        ],
        'alerts': [
            'ALTER TABLE alerts ADD COLUMN created_at DATETIME',
            'ALTER TABLE alerts ADD COLUMN updated_at DATETIME',
            'ALTER TABLE alerts ADD COLUMN created_by INTEGER',
            'ALTER TABLE alerts ADD COLUMN updated_by INTEGER',
            'ALTER TABLE alerts ADD COLUMN is_deleted BOOLEAN DEFAULT 0',
            'ALTER TABLE alerts ADD COLUMN organisation_id INTEGER',
        ],
        'audit_logs': [
            'ALTER TABLE audit_logs ADD COLUMN organisation_id INTEGER',
        ],
    }

    with engine.begin() as conn:
        for table_name, statements in migration_map.items():
            if table_name not in tables:
                continue
            existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
            for stmt in statements:
                target_column = stmt.split('ADD COLUMN ')[1].split(' ')[0]
                if target_column not in existing_columns:
                    conn.execute(text(stmt))
        logger.info('Local SQLite compatibility migrations applied')


initialize_development_database()

# Include routers
app.include_router(api_router, prefix='/api/v1')
app.include_router(mvp_router, prefix='/api')

@app.get('/')
def root():
    """Root endpoint - API information."""
    return {
        'message': 'Welcome to Patrol Pro API',
        'version': settings.API_VERSION,
        'docs': '/api/docs',
    }


@app.get('/health', include_in_schema=True)
def health():
    """Minimal liveness probe for the hosting platform."""
    return {'status': 'ok', 'service': 'patrol-pro-api'}


@app.on_event('startup')
async def startup_event():
    """Handle application startup."""
    logger.info(f"Patrol Pro API {settings.API_VERSION} starting up...")
    logger.info("Application environment: %s", settings.APP_ENV)

@app.on_event('shutdown')
async def shutdown_event():
    """Handle application shutdown."""
    logger.info("Patrol Pro API shutting down...")
