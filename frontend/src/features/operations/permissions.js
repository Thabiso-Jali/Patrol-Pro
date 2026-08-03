export const OPERATIONS_WORKSPACE_PERMISSION = 'operations.workspace.view';

export const canManageTeams = (permissions = []) => permissions.includes('users.manage');
export const canManagePatrols = (permissions = []) => permissions.includes('patrols.manage');
export const canManageWorkforce = (permissions = []) => permissions.includes('users.manage');
