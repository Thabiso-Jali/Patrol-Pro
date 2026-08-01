import React from 'react';
import { renderToString } from 'react-dom/server';

import SettingsPage from './SettingsPage';

const design = {
  colors: { slate900: '#0f172a', slate500: '#64748b' },
  spacing: { md: 12, lg: 20 },
  typography: { headingXL: {}, bodyLg: {} },
};

test('does not claim that unimplemented settings can be persisted', () => {
  const html = renderToString(<SettingsPage {...design} />);
  expect(html).toContain('not yet configurable');
  expect(html).not.toContain('Save Settings');
  expect(html).not.toContain('Settings saved successfully');
});
