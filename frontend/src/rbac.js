export const PERMISSIONS = Object.freeze({
  DASHBOARD_VIEW: 'dashboard.view',
  PATROLS_VIEW: 'patrols.view',
  INCIDENTS_VIEW: 'incidents.view',
  CHECKPOINTS_VIEW: 'checkpoints.view',
  CUSTOMERS_VIEW: 'customers.view',
  DEVICES_VIEW: 'devices.view',
  REPORTS_VIEW: 'reports.read',
  ANALYTICS_VIEW: 'analytics.view',
  USERS_VIEW: 'users.view',
  COMPANY_MANAGE: 'company.manage',
  TEAMS_VIEW: 'teams.view',
});

export const NAV_ITEMS = Object.freeze([
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard', permissions: [PERMISSIONS.DASHBOARD_VIEW] },
  { id: 'patrols', label: 'Patrols', icon: 'patrols', permissions: [PERMISSIONS.PATROLS_VIEW] },
  { id: 'officers', label: 'Officers', icon: 'officers', permissions: [PERMISSIONS.USERS_VIEW] },
  { id: 'teams', label: 'Teams', icon: 'users', permissions: [PERMISSIONS.USERS_VIEW, PERMISSIONS.TEAMS_VIEW] },
  { id: 'my-team', label: 'My Team', icon: 'users', permissions: [PERMISSIONS.TEAMS_VIEW] },
  { id: 'incidents', label: 'Incidents', icon: 'incidents', permissions: [PERMISSIONS.INCIDENTS_VIEW] },
  { id: 'checkpoints', label: 'Checkpoints', icon: 'checkpoints', permissions: [PERMISSIONS.CHECKPOINTS_VIEW] },
  { id: 'reports', label: 'Reports', icon: 'reports', permissions: [PERMISSIONS.REPORTS_VIEW] },
  { id: 'analytics', label: 'Analytics', icon: 'analytics', permissions: [PERMISSIONS.ANALYTICS_VIEW] },
  { id: 'vehicles', label: 'Vehicles', icon: 'vehicles', permissions: [PERMISSIONS.DEVICES_VIEW] },
  { id: 'customers', label: 'Customers', icon: 'customers', permissions: [PERMISSIONS.CUSTOMERS_VIEW] },
  { id: 'users', label: 'Users', icon: 'users', permissions: [PERMISSIONS.USERS_VIEW] },
  { id: 'settings', label: 'Company Settings', icon: 'settings', permissions: [PERMISSIONS.COMPANY_MANAGE] },
]);

export const hasPermission = (grantedPermissions, requiredPermission) => (
  new Set(grantedPermissions || []).has(requiredPermission)
);

export const hasAllPermissions = (grantedPermissions, requiredPermissions = []) => {
  const granted = new Set(grantedPermissions || []);
  return requiredPermissions.every((permission) => granted.has(permission));
};

export const visibleNavigation = (grantedPermissions) => (
  NAV_ITEMS.filter((item) => hasAllPermissions(grantedPermissions, item.permissions))
);

export const canAccessPage = (pageId, grantedPermissions) => {
  const item = NAV_ITEMS.find((candidate) => candidate.id === pageId);
  return Boolean(item && hasAllPermissions(grantedPermissions, item.permissions));
};
