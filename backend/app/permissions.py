from enum import StrEnum


class Permission(StrEnum):
    DASHBOARD_VIEW = 'dashboard.view'
    PATROLS_VIEW = 'patrols.view'
    PATROLS_MANAGE = 'patrols.manage'
    INCIDENTS_VIEW = 'incidents.view'
    INCIDENTS_CREATE = 'incidents.create'
    INCIDENTS_MANAGE = 'incidents.manage'
    CHECKPOINTS_VIEW = 'checkpoints.view'
    CHECKPOINTS_VERIFY = 'checkpoints.verify'
    CHECKPOINTS_MANAGE = 'checkpoints.manage'
    CUSTOMERS_VIEW = 'customers.view'
    CUSTOMERS_MANAGE = 'customers.manage'
    DEVICES_VIEW = 'devices.view'
    DEVICES_MANAGE = 'devices.manage'
    COMMUNICATIONS_VIEW = 'communications.view'
    COMMUNICATIONS_MANAGE = 'communications.manage'
    DOCUMENTS_VIEW = 'documents.view'
    DOCUMENTS_MANAGE = 'documents.manage'
    ANALYTICS_VIEW = 'analytics.view'
    TRACKING_VIEW = 'tracking.view'
    USERS_VIEW = 'users.view'
    TEAMS_VIEW = 'teams.view'
    COMPANY_MANAGE = 'company.manage'
    USERS_MANAGE = 'users.manage'
    USERS_INVITE = 'users.invite'
    OPERATIONS_READ = 'operations.read'
    OPERATIONS_WRITE = 'operations.write'
    REPORTS_READ = 'reports.read'
    AUDIT_READ = 'audit.read'


OPERATION_VIEW_PERMISSIONS = {
    Permission.DASHBOARD_VIEW,
    Permission.PATROLS_VIEW,
    Permission.INCIDENTS_VIEW,
    Permission.CHECKPOINTS_VIEW,
    Permission.COMMUNICATIONS_VIEW,
    Permission.OPERATIONS_READ,
}
FIELD_OPERATION_PERMISSIONS = OPERATION_VIEW_PERMISSIONS | {
    Permission.INCIDENTS_CREATE,
    Permission.CHECKPOINTS_VERIFY,
    Permission.OPERATIONS_WRITE,
    Permission.TEAMS_VIEW,
}
SUPERVISOR_PERMISSIONS = FIELD_OPERATION_PERMISSIONS | {
    Permission.PATROLS_MANAGE,
    Permission.INCIDENTS_MANAGE,
    Permission.CHECKPOINTS_MANAGE,
    Permission.COMMUNICATIONS_MANAGE,
    Permission.CUSTOMERS_VIEW,
    Permission.CUSTOMERS_MANAGE,
    Permission.DEVICES_VIEW,
    Permission.DEVICES_MANAGE,
    Permission.DOCUMENTS_VIEW,
    Permission.DOCUMENTS_MANAGE,
    Permission.REPORTS_READ,
    Permission.ANALYTICS_VIEW,
    Permission.TRACKING_VIEW,
    Permission.AUDIT_READ,
}
MANAGER_PERMISSIONS = SUPERVISOR_PERMISSIONS | {
    Permission.USERS_VIEW,
    Permission.USERS_INVITE,
}
ADMINISTRATOR_PERMISSIONS = MANAGER_PERMISSIONS | {
    Permission.USERS_MANAGE,
}


ROLE_PERMISSIONS = {
    'company_owner': frozenset(Permission),
    'administrator': frozenset(ADMINISTRATOR_PERMISSIONS),
    'manager': frozenset(
        MANAGER_PERMISSIONS
    ),
    'supervisor': frozenset(SUPERVISOR_PERMISSIONS),
    'officer': frozenset(FIELD_OPERATION_PERMISSIONS),
    'employee': frozenset(FIELD_OPERATION_PERMISSIONS),
    'read_only': frozenset(OPERATION_VIEW_PERMISSIONS | {
        Permission.CUSTOMERS_VIEW,
        Permission.DEVICES_VIEW,
        Permission.DOCUMENTS_VIEW,
        Permission.REPORTS_READ,
        Permission.ANALYTICS_VIEW,
    }),
}


def canonical_role(role: str) -> str:
    return role


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(canonical_role(role), frozenset())


def permission_values_for_role(role: str) -> list[str]:
    return sorted(permission.value for permission in permissions_for_role(role))


def has_permissions(role: str, required) -> bool:
    return set(required).issubset(permissions_for_role(role))
