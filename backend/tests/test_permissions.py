from backend.app.permissions import Permission, canonical_role, permissions_for_role


def test_company_owner_has_every_permission():
    assert permissions_for_role('company_owner') == frozenset(Permission)


def test_enterprise_role_boundaries():
    administrator = permissions_for_role('administrator')
    manager = permissions_for_role('manager')
    supervisor = permissions_for_role('supervisor')
    employee = permissions_for_role('employee')

    assert Permission.USERS_MANAGE in administrator
    assert Permission.COMPANY_MANAGE not in administrator
    assert Permission.USERS_INVITE in manager
    assert Permission.USERS_MANAGE not in manager
    assert Permission.REPORTS_READ in supervisor
    assert Permission.USERS_INVITE not in supervisor
    assert Permission.PATROLS_MANAGE in supervisor
    assert Permission.AUDIT_READ in supervisor
    assert Permission.INCIDENTS_CREATE in employee
    assert Permission.PATROLS_MANAGE not in employee
    assert Permission.REPORTS_READ not in employee


def test_officer_and_employee_are_canonical_operational_roles():
    assert canonical_role('officer') == 'officer'
    assert permissions_for_role('officer') == permissions_for_role('employee')


def test_removed_communications_ui_does_not_leave_misleading_permissions():
    permission_values = {permission.value for permission in Permission}
    assert 'communications.view' not in permission_values
    assert 'communications.manage' not in permission_values
    assert Permission.NOTIFICATIONS_VIEW in permissions_for_role('employee')
