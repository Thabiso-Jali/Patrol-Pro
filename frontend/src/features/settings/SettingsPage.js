import React from 'react';

import OperationStatus from '../../components/OperationStatus';

export default function SettingsPage({ colors, spacing, typography }) {
  return (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>
          Company Settings
        </h1>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Organisation-wide operational settings are not yet configurable.
        </p>
      </div>
      <OperationStatus
        state="idle"
        message="Settings will become editable only when they are validated, organisation-scoped and persisted by the backend. No changes can be saved from this page."
      />
    </div>
  );
}
