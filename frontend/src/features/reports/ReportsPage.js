import React from 'react';

import OperationStatus from '../../components/OperationStatus';

export default function ReportsPage({ colors, spacing, typography }) {
  return (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>
          Reports
        </h1>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Daily Activity Reports are not yet available.
        </p>
      </div>
      <OperationStatus
        state="idle"
        message="Persisted, reviewable and downloadable Daily Activity Reports will be implemented during the reporting phase. No report has been generated, exported or delivered from this page."
      />
    </div>
  );
}
