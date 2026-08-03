import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

import OperationsWorkspacePage from '../OperationsWorkspacePage';
import { filterStaff } from '../selectors';

global.IS_REACT_ACT_ENVIRONMENT = true;

const payload = {
  as_of: '2026-08-03T12:00:00Z',
  availability_definition: 'Assignment availability only; it does not represent presence.',
  metric_definitions: {},
  metrics: {
    active_workforce: 2, available_workforce: 1, deployed_workforce: 1,
    inactive_workforce: 1, workforce_without_team: 1, active_teams: 1,
    active_patrols: 1,
  },
  staff: [
    { id: 1, full_name: 'Alex Smith', staff_identifier: 'PP-00001', role: 'employee', account_status: 'active', availability_status: 'deployed', team_id: 5, team_name: 'Team Alpha', current_patrols: ['North Patrol'] },
    { id: 2, full_name: 'Jamie Jones', staff_identifier: 'PP-00002', role: 'officer', account_status: 'active', availability_status: 'available', team_id: null, team_name: null, current_patrols: [] },
    { id: 3, full_name: 'Inactive Person', staff_identifier: 'PP-00003', role: 'employee', account_status: 'inactive', availability_status: 'inactive', team_id: 5, team_name: 'Team Alpha', current_patrols: [] },
  ],
  teams: [{ id: 5, name: 'Team Alpha', status: 'active', leader_user_id: 1, leader_name: 'Alex Smith', active_member_count: 1, inactive_member_count: 1, available_member_count: 0, deployed_member_count: 1, current_patrols: ['North Patrol'], attention: [] }],
};

const renderPage = (apiCall, permissions = ['operations.workspace.view']) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<OperationsWorkspacePage apiCall={apiCall} permissions={permissions} onNavigate={jest.fn()} />));
  return { container, cleanup: () => { act(() => root.unmount()); container.remove(); } };
};

const flush = async () => act(async () => { await Promise.resolve(); await Promise.resolve(); });

test('shows loading before rendering authoritative summary and coverage', async () => {
  let resolve;
  const apiCall = jest.fn(() => new Promise((done) => { resolve = done; }));
  const view = renderPage(apiCall);
  expect(view.container.textContent).toContain('Loading the current staffing snapshot');
  await act(async () => resolve({ ok: true, data: payload }));
  await flush();
  expect(view.container.textContent).toContain('Operations Workspace');
  expect(view.container.textContent).toContain('Alex Smith');
  expect(view.container.textContent).toContain('Currently deployed');
  expect(view.container.textContent).toContain('Staffing target: Unavailable');
  expect(view.container.textContent).toContain('does not represent presence');
  view.cleanup();
});

test('truthful empty organisation and filtered empty states are distinct', async () => {
  const apiCall = jest.fn().mockResolvedValue({ ok: true, data: {
    ...payload,
    metrics: Object.fromEntries(Object.keys(payload.metrics).map((key) => [key, 0])),
    staff: [], teams: [],
  } });
  const view = renderPage(apiCall);
  await flush();
  expect(view.container.textContent).toContain('No staff match this view');
  expect(view.container.textContent).toContain('No operational workforce records');
  expect(view.container.textContent).toContain('No Teams found');
  view.cleanup();
});

test('API error renders no operational figures and supports retry', async () => {
  const apiCall = jest.fn().mockResolvedValue({ ok: false, data: null });
  const view = renderPage(apiCall);
  await flush();
  expect(view.container.getAttribute('role')).toBeNull();
  expect(view.container.textContent).toContain('No operational figures are being shown');
  expect(view.container.textContent).not.toContain('Active workforce');
  const retry = Array.from(view.container.querySelectorAll('button')).find((button) => button.textContent === 'Retry');
  act(() => retry.click());
  expect(apiCall).toHaveBeenCalledTimes(2);
  view.cleanup();
});

test('filters support staff ID, availability, team and current assignment', () => {
  expect(filterStaff(payload.staff, { search: 'PP-00002', availability: 'available', team: 'none', assignment: 'unassigned', account: 'active' }))
    .toEqual([payload.staff[1]]);
  expect(filterStaff(payload.staff, { search: '', availability: 'deployed', team: '5', assignment: 'assigned', account: 'active' }))
    .toEqual([payload.staff[0]]);
});

test('correction actions are permission-controlled and filters are labelled', async () => {
  const view = renderPage(jest.fn().mockResolvedValue({ ok: true, data: payload }), ['operations.workspace.view']);
  await flush();
  expect(view.container.textContent).toContain('workspace is read-only');
  expect(view.container.textContent).not.toContain('Manage teams');
  expect(view.container.querySelector('input[type="search"]').labels[0].textContent).toContain('Search staff');
  view.cleanup();
});

test('workforce correction requires manage capability rather than view capability', async () => {
  const viewOnly = renderPage(
    jest.fn().mockResolvedValue({ ok: true, data: payload }),
    ['operations.workspace.view', 'users.view'],
  );
  await flush();
  expect(viewOnly.container.textContent).not.toContain('Review workforce accounts');
  viewOnly.cleanup();

  const manager = renderPage(
    jest.fn().mockResolvedValue({ ok: true, data: payload }),
    ['operations.workspace.view', 'users.manage'],
  );
  await flush();
  expect(manager.container.textContent).toContain('Review workforce accounts');
  expect(manager.container.textContent).toContain('Manage teams');
  manager.cleanup();
});

test('Team coverage renders factual warnings without claiming understaffing', async () => {
  const warned = {
    ...payload,
    teams: [{
      ...payload.teams[0], leader_user_id: null, leader_name: null,
      active_member_count: 0, inactive_member_count: 1,
      available_member_count: 0, deployed_member_count: 0,
      attention: ['No active members', 'No leader assigned', 'Team leader is inactive'],
    }],
  };
  const view = renderPage(jest.fn().mockResolvedValue({ ok: true, data: warned }));
  await flush();
  expect(view.container.textContent).toContain('Attention: No active members');
  expect(view.container.textContent).toContain('Attention: No leader assigned');
  expect(view.container.textContent).toContain('Attention: Team leader is inactive');
  expect(view.container.textContent).not.toContain('understaffed');
  view.cleanup();
});
