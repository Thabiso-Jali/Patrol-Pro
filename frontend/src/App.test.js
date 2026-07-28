import React from 'react';
import { renderToString } from 'react-dom/server';

import App from './App';

test('renders without crashing', () => {
  expect(renderToString(<App />)).not.toBe('');
});
