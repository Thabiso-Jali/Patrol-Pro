import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .config import get_settings
from .database import engine, Base
from .middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
from .api.api_v1.api import api_router
from .api.mvp import router as mvp_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
Base.metadata.create_all(bind=engine)
logger.info("Database initialized")

# Get settings
settings = get_settings()
settings.validate_production_safety()

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
logger.info(f"CORS configured for origins: {settings.ALLOWED_ORIGINS}")


def apply_runtime_migrations() -> None:
    """Backfill newly introduced columns for local SQLite deployments.

    This keeps dev/test environments running without a full migration tool.
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    migration_map = {
        'users': [
            "ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'officer'",
            "ALTER TABLE users ADD COLUMN created_at DATETIME",
            "ALTER TABLE users ADD COLUMN updated_at DATETIME",
            "ALTER TABLE users ADD COLUMN created_by INTEGER",
            "ALTER TABLE users ADD COLUMN updated_by INTEGER",
            "ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN organisation_id INTEGER",
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
        logger.info('Runtime migrations applied')


apply_runtime_migrations()

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

@app.on_event('startup')
async def startup_event():
    """Handle application startup."""
    logger.info(f"Patrol Pro API {settings.API_VERSION} starting up...")
    logger.info(f"Running in {'DEBUG' if settings.DEBUG else 'PRODUCTION'} mode")

@app.on_event('shutdown')
async def shutdown_event():
    """Handle application shutdown."""
    logger.info("Patrol Pro API shutting down...")
