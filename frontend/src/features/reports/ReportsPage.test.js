import React from 'react';
import { renderToString } from 'react-dom/server';

import ReportsPage from './ReportsPage';

const design = {
  colors: { slate900: '#0f172a', slate500: '#64748b' },
  spacing: { md: 12, lg: 20 },
  typography: { headingXL: {}, bodyLg: {} },
};

test('does not offer fake report persistence or export actions', () => {
  const html = renderToString(<ReportsPage {...design} />);
  expect(html).toContain('Daily Activity Reports are not yet available');
  expect(html).not.toContain('Generate Report');
  expect(html).not.toContain('Export');
  expect(html).not.toContain('Refresh');
  expect(html).not.toContain('Delivered');
});
