import {
  NAV_ITEMS,
  PERMISSIONS,
  canAccessPage,
  hasPermission,
  visibleNavigation,
} from './rbac';

const ids = (permissions) => visibleNavigation(permissions).map((item) => item.id);

const operational = [
  PERMISSIONS.DASHBOARD_VIEW,
  PERMISSIONS.PATROLS_VIEW,
  PERMISSIONS.INCIDENTS_VIEW,
  PERMISSIONS.CHECKPOINTS_VIEW,
  PERMISSIONS.TEAMS_VIEW,
];

test('company owner permissions reveal every navigation item', () => {
  const everyPermission = Object.values(PERMISSIONS);
  expect(ids(everyPermission)).toEqual(NAV_ITEMS.map((item) => item.id));
});

test('administrator navigation excludes company-owner settings without company permission', () => {
  const administrator = [
    ...operational,
    PERMISSIONS.USERS_VIEW,
    PERMISSIONS.REPORTS_VIEW,
    PERMISSIONS.ANALYTICS_VIEW,
    PERMISSIONS.DEVICES_VIEW,
    PERMISSIONS.CUSTOMERS_VIEW,
  ];
  expect(ids(administrator)).toContain('users');
  expect(ids(administrator)).not.toContain('settings');
});

test('manager and supervisor navigation is derived only from granted permissions', () => {
  const manager = [...operational, PERMISSIONS.USERS_VIEW, PERMISSIONS.REPORTS_VIEW];
  const supervisor = [...operational, PERMISSIONS.REPORTS_VIEW];
  expect(ids(manager)).toContain('users');
  expect(ids(supervisor)).not.toContain('users');
});

test.each(['officer', 'employee'])('%s operational permissions never produce an empty sidebar', () => {
  expect(ids(operational)).toEqual([
    'dashboard',
    'patrols',
    'my-team',
    'incidents',
    'checkpoints',
  ]);
});

test('customers are named truthfully and communications are not exposed', () => {
  const navigation = NAV_ITEMS.map((item) => ({ id: item.id, label: item.label }));
  expect(navigation).toContainEqual({ id: 'customers', label: 'Customers' });
  expect(navigation.some((item) => item.id === 'documents')).toBe(false);
  expect(navigation.some((item) => item.id === 'communications')).toBe(false);
});

test('manual page access is denied when its permission is absent', () => {
  expect(canAccessPage('users', operational)).toBe(false);
  expect(canAccessPage('patrols', operational)).toBe(true);
  expect(hasPermission(operational, PERMISSIONS.COMPANY_MANAGE)).toBe(false);
});

test('a future custom role works without changing navigation code', () => {
  const customRolePermissions = [PERMISSIONS.DASHBOARD_VIEW, PERMISSIONS.REPORTS_VIEW];
  expect(ids(customRolePermissions)).toEqual(['dashboard', 'reports']);
});
