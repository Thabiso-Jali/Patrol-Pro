import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { renderToString } from 'react-dom/server';

import OperationStatus, { OPERATION_STATES } from './OperationStatus';

global.IS_REACT_ACT_ENVIRONMENT = true;

test.each(Object.keys(OPERATION_STATES))('renders the %s operation state accessibly', (state) => {
  const authoritative = Boolean(OPERATION_STATES[state].requiresAuthority);
  const html = renderToString(
    <OperationStatus state={state} message="Status detail" authoritative={authoritative} />
  );
  if (state === 'idle') {
    expect(html).not.toContain('aria-live=');
    expect(html).not.toContain('role="status"');
  } else {
    expect(html).toContain('aria-live=');
  }
  expect(html).toContain('Status detail');
});

test.each(['successful', 'partially_completed', 'synchronised'])(
  'rejects non-authoritative %s state usage',
  (state) => {
    expect(() => renderToString(<OperationStatus state={state} message="Unconfirmed" />))
      .toThrow('requires authoritative confirmation');
  }
);

test('offers a contextual retry only when a real retry callback exists', () => {
  const retry = jest.fn();
  const container = document.createElement('div');
  const root = createRoot(container);
  act(() => root.render(
    <OperationStatus state="failed" message="Request failed" onRetry={retry} />
  ));
  const button = container.querySelector('button');
  expect(button.textContent).toBe('Try again');
  act(() => button.click());
  expect(retry).toHaveBeenCalledTimes(1);
  act(() => root.unmount());
});
