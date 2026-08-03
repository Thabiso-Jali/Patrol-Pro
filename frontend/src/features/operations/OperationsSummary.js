import React from 'react';

const METRICS = [
  ['active_workforce', 'Active workforce'],
  ['available_workforce', 'Available now'],
  ['deployed_workforce', 'Currently deployed'],
  ['inactive_workforce', 'Inactive workforce'],
  ['workforce_without_team', 'Without a team'],
  ['active_teams', 'Active teams'],
  ['active_patrols', 'Current patrols'],
];

export default function OperationsSummary({ metrics }) {
  return (
    <section aria-labelledby="operations-summary-heading">
      <h2 id="operations-summary-heading">Staffing summary</h2>
      <div className="operations-summary-grid">
        {METRICS.map(([key, label]) => (
          <article className="operations-metric" key={key}>
            <span>{label}</span>
            <strong>{metrics[key]}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}
