from enum import StrEnum


class Permission(StrEnum):
    COMPANY_MANAGE = 'company.manage'
    USERS_MANAGE = 'users.manage'
    USERS_INVITE = 'users.invite'
    OPERATIONS_READ = 'operations.read'
    OPERATIONS_WRITE = 'operations.write'
    REPORTS_READ = 'reports.read'
    AUDIT_READ = 'audit.read'


ROLE_ALIASES = {
    'admin': 'administrator',
    'officer': 'employee',
}


ROLE_PERMISSIONS = {
    'company_owner': frozenset(Permission),
    'administrator': frozenset(Permission),
    'manager': frozenset(
        {
            Permission.USERS_INVITE,
            Permission.OPERATIONS_READ,
            Permission.OPERATIONS_WRITE,
            Permission.REPORTS_READ,
            Permission.AUDIT_READ,
        }
    ),
    'supervisor': frozenset(
        {
            Permission.OPERATIONS_READ,
            Permission.OPERATIONS_WRITE,
            Permission.REPORTS_READ,
        }
    ),
    'employee': frozenset({Permission.OPERATIONS_READ, Permission.OPERATIONS_WRITE}),
    'read_only': frozenset({Permission.OPERATIONS_READ, Permission.REPORTS_READ}),
}


def canonical_role(role: str) -> str:
    return ROLE_ALIASES.get(role, role)


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(canonical_role(role), frozenset())


def has_permissions(role: str, required) -> bool:
    return set(required).issubset(permissions_for_role(role))
