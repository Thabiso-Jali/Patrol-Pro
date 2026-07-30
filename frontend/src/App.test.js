import React, { act, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { renderToString } from 'react-dom/server';

import App, {
  DashboardContent,
  MobileNavigation,
  SearchableMultiSelect,
  additionalOfficerChoices,
  getDefaultPatrolSchedule,
  recommendedFormAssignment,
  staffingCoverage,
} from './App';

global.IS_REACT_ACT_ENVIRONMENT = true;
window.matchMedia = window.matchMedia || (() => ({
  matches: false,
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
}));

const emptyStats = {
  active_patrols: 0,
  officers: 0,
  open_incidents: 0,
  pending_checkpoints: 0,
  completed_checkpoints: 0,
  checkpoint_completion_rate: 0,
  recent_activity: [],
  active_patrol_details: [],
  todays_schedule: [],
};

const mobileItems = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'patrols', label: 'Patrols', icon: 'patrols' },
];

const NavigationHarness = () => {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState('dashboard');
  return (
    <div data-active={active}>
      <button aria-label="Open navigation" onClick={() => setOpen(true)}>Menu</button>
      <MobileNavigation
        open={open}
        items={mobileItems}
        activeNav={active}
        onSelect={setActive}
        onClose={() => setOpen(false)}
        onLogout={() => setOpen(false)}
      />
    </div>
  );
};

const renderInteractive = (element) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(element));
  return {
    container,
    cleanup: () => {
      act(() => root.unmount());
      container.remove();
    },
  };
};

const jsonResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  text: async () => (data === null ? '' : JSON.stringify(data)),
});

const changeInput = (input, value) => {
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    'value'
  ).set;
  setter.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
};

const flushPromises = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
};

const submitLogin = async (view) => {
  const emailInput = view.container.querySelector('input[type="text"]');
  const passwordInput = view.container.querySelector('input[type="password"]');
  act(() => {
    changeInput(emailInput, 'owner@example.com');
    changeInput(passwordInput, 'StrongPass123!');
  });
  const signIn = Array.from(view.container.querySelectorAll('button'))
    .find((button) => button.textContent === 'Sign In');
  act(() => signIn.click());
  await flushPromises();
};

test('renders without crashing', () => {
  expect(renderToString(<App />)).not.toBe('');
});

test('dashboard shows a loading state', () => {
  const html = renderToString(<DashboardContent stats={null} isLoading error="" />);
  expect(html).toContain('Loading dashboard statistics...');
});

test('dashboard renders statistics returned by the API', () => {
  const html = renderToString(
    <DashboardContent
      stats={{
        ...emptyStats,
        active_patrols: 3,
        officers: 7,
        open_incidents: 2,
        pending_checkpoints: 5,
      }}
      isLoading={false}
      error=""
    />
  );

  expect(html).toContain('Active Patrols');
  expect(html).toContain('>3<');
  expect(html).toContain('>7<');
  expect(html).toContain('>2<');
  expect(html).toContain('>5<');
});

test('dashboard renders successful empty values as zero', () => {
  const html = renderToString(<DashboardContent stats={emptyStats} isLoading={false} error="" />);
  expect((html.match(/>0</g) || []).length).toBeGreaterThanOrEqual(4);
  expect(html).toContain('No recent activity.');
  expect(html).toContain('No results');
});

test('dashboard API failure shows an error without fabricated figures', () => {
  const html = renderToString(
    <DashboardContent stats={null} isLoading={false} error="request failed" />
  );
  expect(html).toContain('Dashboard statistics are unavailable. Please try again.');
  expect(html).not.toContain('>12<');
  expect(html).not.toContain('vs last week');
});

const staffingAvailability = {
  available_teams: [{
    id: 10,
    name: 'Team Alpha',
    members: [
      { id: 1, full_name: 'One', staff_identifier: 'PP-00001' },
      { id: 2, full_name: 'Two', staff_identifier: 'PP-00002' },
    ],
  }],
  unavailable_teams: [],
  available_officers: [
    { id: 1, full_name: 'One', staff_identifier: 'PP-00001' },
    { id: 2, full_name: 'Two', staff_identifier: 'PP-00002' },
    { id: 3, full_name: 'Three', staff_identifier: 'PP-00003' },
  ],
};

test('staffing coverage counts team members and extras without duplication', () => {
  const coverage = staffingCoverage({
    team_ids: [10],
    officer_ids: [2, 3],
    required_officers: 4,
  }, staffingAvailability);
  expect(coverage.assigned).toBe(3);
  expect(coverage.missing).toBe(1);
});

test('selected team members are removed from additional officer choices', () => {
  expect(additionalOfficerChoices(staffingAvailability, [10]).map((officer) => officer.id))
    .toEqual([3]);
});

test('one-click recommendation replaces the current structured assignment', () => {
  expect(recommendedFormAssignment(
    { name: 'Patrol', team_ids: [], officer_ids: [99] },
    { team_ids: [10], officer_ids: [3] },
  )).toEqual({ name: 'Patrol', team_ids: [10], officer_ids: [3] });
});

test('default patrol schedule starts on a practical interval and lasts eight hours', () => {
  const schedule = getDefaultPatrolSchedule(new Date(2026, 6, 30, 10, 7, 20));
  expect(schedule.start_time).toBe('2026-07-30T10:15');
  expect(
    new Date(schedule.end_time).getTime() - new Date(schedule.start_time).getTime()
  ).toBe(8 * 60 * 60 * 1000);
});

test('searchable multi-select remains label and checkbox accessible', () => {
  const onChange = jest.fn();
  const view = renderInteractive(
    <SearchableMultiSelect
      label="Assign Available Officers"
      options={[
        { value: 1, label: 'Officer One · PP-00001' },
        { value: 2, label: 'Officer Two · PP-00002' },
      ]}
      selected={[]}
      onChange={onChange}
    />
  );
  const search = view.container.querySelector('input[type="search"]');
  act(() => changeInput(search, 'Two'));
  expect(view.container.textContent).not.toContain('Officer One');
  expect(view.container.textContent).toContain('Officer Two');
  const checkbox = view.container.querySelector('input[type="checkbox"]');
  act(() => checkbox.click());
  expect(onChange).toHaveBeenCalledWith([2]);
  view.cleanup();
});

test('mobile navigation opens and closes from its backdrop', () => {
  const view = renderInteractive(<NavigationHarness />);
  const openButton = view.container.querySelector('[aria-label="Open navigation"]');

  act(() => openButton.click());
  expect(view.container.querySelector('[role="dialog"][aria-label="Main navigation"]')).not.toBeNull();
  expect(document.body.style.overflow).toBe('hidden');

  act(() => view.container.querySelector('.pp-drawer-backdrop').click());
  expect(view.container.querySelector('[role="dialog"][aria-label="Main navigation"]')).toBeNull();
  expect(document.body.style.overflow).toBe('');
  view.cleanup();
});

test('selecting a mobile navigation item changes page and closes the drawer', () => {
  const view = renderInteractive(<NavigationHarness />);

  act(() => view.container.querySelector('[aria-label="Open navigation"]').click());
  const patrolsButton = Array.from(view.container.querySelectorAll('.pp-drawer-nav-item'))
    .find((button) => button.textContent.includes('Patrols'));
  act(() => patrolsButton.click());

  expect(view.container.firstChild.getAttribute('data-active')).toBe('patrols');
  expect(view.container.querySelector('[role="dialog"][aria-label="Main navigation"]')).toBeNull();
  view.cleanup();
});

test('protected navigation is not exposed while the permission response is pending', async () => {
  let resolveContext;
  const contextPromise = new Promise((resolve) => { resolveContext = resolve; });
  global.fetch = jest.fn((url) => {
    if (url.endsWith('/auth/token')) {
      return Promise.resolve(jsonResponse({ access_token: 'token', refresh_token: 'refresh' }));
    }
    if (url.endsWith('/auth/me')) return contextPromise;
    throw new Error(`Unexpected request: ${url}`);
  });
  const view = renderInteractive(<App />);
  await submitLogin(view);
  await flushPromises();

  expect(view.container.querySelector('.pp-desktop-sidebar')).toBeNull();
  expect(view.container.textContent).not.toContain('Company Settings');

  resolveContext(jsonResponse({
    user: { id: 1, email: 'owner@example.com', role: 'company_owner' },
    company: { id: 1, name: 'Test Company' },
    role: 'company_owner',
    permissions: ['dashboard.view'],
  }));
  await flushPromises();
  view.cleanup();
});

test('login uses server permissions and logout revokes the backend session', async () => {
  global.fetch = jest.fn((url) => {
    if (url.endsWith('/auth/token')) {
      return Promise.resolve(jsonResponse({ access_token: 'token', refresh_token: 'refresh' }));
    }
    if (url.endsWith('/auth/me')) {
      return Promise.resolve(jsonResponse({
        user: { id: 1, email: 'owner@example.com', role: 'company_owner' },
        company: { id: 1, name: 'Test Company' },
        role: 'company_owner',
        permissions: ['dashboard.view'],
      }));
    }
    if (url.endsWith('/dashboard/stats')) return Promise.resolve(jsonResponse(emptyStats));
    if (url.endsWith('/auth/logout')) return Promise.resolve(jsonResponse(null, 204));
    throw new Error(`Unexpected request: ${url}`);
  });
  const view = renderInteractive(<App />);
  await submitLogin(view);
  await flushPromises();

  expect(view.container.querySelector('.pp-desktop-sidebar')).not.toBeNull();
  expect(view.container.textContent).toContain('Dashboard');
  expect(view.container.textContent).not.toContain('Company Settings');

  const logout = Array.from(view.container.querySelectorAll('button'))
    .find((button) => button.textContent.includes('Logout'));
  await act(async () => logout.click());
  await flushPromises();
  expect(global.fetch).toHaveBeenCalledWith(
    expect.stringContaining('/auth/logout'),
    expect.objectContaining({ method: 'POST' })
  );
  expect(view.container.textContent).toContain('Sign In');
  view.cleanup();
});

test('officers page renders accepted operational users from the API', async () => {
  global.fetch = jest.fn((url) => {
    if (url.endsWith('/auth/token')) {
      return Promise.resolve(jsonResponse({ access_token: 'token', refresh_token: 'refresh' }));
    }
    if (url.endsWith('/auth/me')) {
      return Promise.resolve(jsonResponse({
        user: { id: 1, email: 'owner@example.com', role: 'company_owner' },
        company: { id: 1, name: 'Test Company' },
        role: 'company_owner',
        permissions: ['dashboard.view', 'users.view'],
      }));
    }
    if (url.endsWith('/dashboard/stats')) return Promise.resolve(jsonResponse(emptyStats));
    if (url.endsWith('/users/officers')) {
      return Promise.resolve(jsonResponse([{
        id: 2,
        email: 'employee@example.com',
        full_name: 'Accepted Employee',
        role: 'employee',
        organisation_id: 1,
      }]));
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const view = renderInteractive(<App />);
  await submitLogin(view);
  await flushPromises();

  const officersLink = Array.from(view.container.querySelectorAll('button'))
    .find((button) => button.textContent.includes('Officers'));
  act(() => officersLink.click());

  expect(view.container.textContent).toContain('Accepted Employee');
  expect(view.container.textContent).toContain('employee@example.com');
  view.cleanup();
});

test('employee My Team view shows safe coworker names and staff IDs', async () => {
  global.fetch = jest.fn((url) => {
    if (url.endsWith('/auth/token')) {
      return Promise.resolve(jsonResponse({ access_token: 'token', refresh_token: 'refresh' }));
    }
    if (url.endsWith('/auth/me')) {
      return Promise.resolve(jsonResponse({
        user: { id: 2, email: 'employee@example.com', role: 'employee' },
        company: { id: 1, name: 'Test Company' },
        role: 'employee',
        permissions: ['teams.view'],
      }));
    }
    if (url.endsWith('/teams/mine')) {
      return Promise.resolve(jsonResponse({
        id: 1,
        name: 'Team Alpha',
        leader_user_id: 2,
        status: 'active',
        availability: 'available',
        active_patrols: [],
        members: [
          { id: 2, full_name: 'Officer Smith', staff_identifier: 'PP-00002', role: 'employee' },
          { id: 3, full_name: 'Officer Jones', staff_identifier: 'PP-00003', role: 'employee' },
        ],
      }));
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const view = renderInteractive(<App />);
  await submitLogin(view);
  await flushPromises();

  const myTeamLink = Array.from(view.container.querySelectorAll('button'))
    .find((button) => button.textContent.includes('My Team'));
  act(() => myTeamLink.click());

  expect(view.container.textContent).toContain('Team Alpha');
  expect(view.container.textContent).toContain('Officer Jones');
  expect(view.container.textContent).toContain('PP-00003');
  view.cleanup();
});

test('an expired access token clears protected content safely', async () => {
  global.fetch = jest.fn((url) => {
    if (url.endsWith('/auth/token')) {
      return Promise.resolve(jsonResponse({ access_token: 'expired', refresh_token: 'refresh' }));
    }
    if (url.endsWith('/auth/me')) {
      return Promise.resolve(jsonResponse({
        user: { id: 1, email: 'owner@example.com', role: 'company_owner' },
        company: { id: 1, name: 'Test Company' },
        role: 'company_owner',
        permissions: ['dashboard.view'],
      }));
    }
    if (url.endsWith('/dashboard/stats')) {
      return Promise.resolve(jsonResponse({ detail: 'Could not validate credentials' }, 401));
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  const view = renderInteractive(<App />);
  await submitLogin(view);
  await flushPromises();
  await flushPromises();

  expect(view.container.querySelector('.pp-desktop-sidebar')).toBeNull();
  expect(view.container.textContent).toContain('Sign In');
  view.cleanup();
});
