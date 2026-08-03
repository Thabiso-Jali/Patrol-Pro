import React from 'react';

const Field = ({ label, children }) => (
  <label className="operations-filter">
    <span>{label}</span>
    {children}
  </label>
);

export default function OperationsFilters({ filters, setFilters, teams, resultCount }) {
  const update = (key) => (event) => setFilters((current) => ({
    ...current,
    [key]: event.target.value,
  }));
  return (
    <section className="operations-filters" aria-labelledby="staff-filters-heading">
      <div className="operations-section-heading">
        <h2 id="staff-filters-heading">Staffing visibility</h2>
        <span aria-live="polite">{resultCount} result{resultCount === 1 ? '' : 's'}</span>
      </div>
      <div className="operations-filter-grid">
        <Field label="Search staff">
          <input type="search" value={filters.search} onChange={update('search')} placeholder="Name or staff ID" />
        </Field>
        <Field label="Current status">
          <select value={filters.availability} onChange={update('availability')}>
            <option value="all">All statuses</option>
            <option value="available">Available</option>
            <option value="deployed">Currently deployed</option>
            <option value="inactive">Inactive</option>
          </select>
        </Field>
        <Field label="Team">
          <select value={filters.team} onChange={update('team')}>
            <option value="all">All teams</option>
            <option value="none">Without a team</option>
            {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
          </select>
        </Field>
        <Field label="Current patrol">
          <select value={filters.assignment} onChange={update('assignment')}>
            <option value="all">Assigned and unassigned</option>
            <option value="assigned">Assigned</option>
            <option value="unassigned">Unassigned</option>
          </select>
        </Field>
        <Field label="Account">
          <select value={filters.account} onChange={update('account')}>
            <option value="all">Active and inactive</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </Field>
      </div>
    </section>
  );
}
