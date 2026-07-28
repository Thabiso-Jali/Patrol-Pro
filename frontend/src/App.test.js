import React from 'react';
import { renderToString } from 'react-dom/server';

import App, { DashboardContent } from './App';

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
