import React from 'react';

export const OPERATION_STATES = Object.freeze({
  idle: { label: 'Ready', tone: 'neutral', live: 'off' },
  pending: { label: 'Working', tone: 'info', live: 'polite' },
  successful: { label: 'Completed', tone: 'success', live: 'polite', requiresAuthority: true },
  failed: { label: 'Failed', tone: 'error', live: 'assertive' },
  partially_completed: { label: 'Partially completed', tone: 'warning', live: 'polite', requiresAuthority: true },
  saved_on_device: { label: 'Saved on device', tone: 'warning', live: 'polite' },
  waiting_to_sync: { label: 'Waiting to sync', tone: 'warning', live: 'polite' },
  uploading: { label: 'Uploading', tone: 'info', live: 'polite' },
  synchronised: { label: 'Synchronised', tone: 'success', live: 'polite', requiresAuthority: true },
  conflict: { label: 'Conflict requiring review', tone: 'error', live: 'assertive' },
});

const tones = {
  neutral: { background: '#F1F5F9', border: '#CBD5E1', color: '#334155' },
  info: { background: '#EFF6FF', border: '#93C5FD', color: '#1E40AF' },
  success: { background: '#F0FDF4', border: '#86EFAC', color: '#166534' },
  warning: { background: '#FFFBEB', border: '#FCD34D', color: '#92400E' },
  error: { background: '#FEF2F2', border: '#FCA5A5', color: '#991B1B' },
};

export default function OperationStatus({
  state = 'idle',
  message,
  retryLabel = 'Try again',
  onRetry,
  authoritative = false,
}) {
  const definition = OPERATION_STATES[state] || OPERATION_STATES.idle;
  if (definition.requiresAuthority && !authoritative) {
    throw new Error(
      `OperationStatus state "${state}" requires authoritative confirmation`
    );
  }
  const tone = tones[definition.tone];
  const isIdle = state === 'idle';

  return (
    <div
      role={isIdle ? undefined : definition.live === 'assertive' ? 'alert' : 'status'}
      aria-live={isIdle ? undefined : definition.live}
      aria-atomic={isIdle ? undefined : 'true'}
      style={{
        padding: '16px',
        border: `1px solid ${tone.border}`,
        borderRadius: '10px',
        background: tone.background,
        color: tone.color,
      }}
    >
      <strong>{definition.label}</strong>
      {message && <p style={{ margin: '6px 0 0' }}>{message}</p>}
      {state === 'failed' && typeof onRetry === 'function' && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            marginTop: '12px',
            border: `1px solid ${tone.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            background: '#FFFFFF',
            color: tone.color,
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}
