import React from 'react';

const statusLabel = (status) => ({
  available: 'Available',
  deployed: 'Currently deployed',
  inactive: 'Inactive',
}[status] || 'Status unavailable');

export default function StaffAvailabilityList({ staff, emptyDetail }) {
  if (staff.length === 0) {
    return <div className="operations-empty"><strong>No staff match this view.</strong><p>{emptyDetail}</p></div>;
  }
  return (
    <div className="operations-list" aria-label="Staffing results">
      {staff.map((person) => (
        <article className="operations-staff-row" key={person.id}>
          <div>
            <h3>{person.full_name || 'Name unavailable'}</h3>
            <p>{person.staff_identifier} · {person.team_name || 'No team assigned'}</p>
          </div>
          <div className="operations-staff-state">
            <span className={`operations-status operations-status--${person.availability_status}`}>
              {statusLabel(person.availability_status)}
            </span>
            <p>{person.current_patrols.length > 0
              ? person.current_patrols.join(', ')
              : person.account_status === 'active' ? 'No current patrol' : 'Account inactive'}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
