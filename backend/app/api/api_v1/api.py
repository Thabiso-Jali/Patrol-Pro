from fastapi import APIRouter
from .endpoints import (
    alerts,
    audit_logs,
    auth,
    checkpoints,
    customers,
    devices,
    health,
    notifications,
    operations,
    patrols,
    reports,
    tracking,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=['health'])
api_router.include_router(users.router, prefix='/users', tags=['users'])
api_router.include_router(patrols.router, prefix='/patrols', tags=['patrols'])
api_router.include_router(devices.router, prefix='/devices', tags=['devices'])
api_router.include_router(customers.router, prefix='/customers', tags=['customers'])
api_router.include_router(alerts.router, prefix='/alerts', tags=['alerts'])
api_router.include_router(checkpoints.router, prefix='/checkpoints', tags=['checkpoints'])
api_router.include_router(tracking.router, prefix='/tracking', tags=['tracking'])
api_router.include_router(notifications.router, prefix='/notifications', tags=['notifications'])
api_router.include_router(audit_logs.router, prefix='/audit-logs', tags=['audit-logs'])
api_router.include_router(operations.router, prefix='/operations', tags=['operations'])
api_router.include_router(reports.router, prefix='/reports', tags=['reports'])
api_router.include_router(auth.router, prefix='/auth', tags=['auth'])
