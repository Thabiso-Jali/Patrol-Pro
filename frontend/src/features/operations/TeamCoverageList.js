import React from 'react';

export default function TeamCoverageList({ teams, onNavigate, canCorrectTeams }) {
  return (
    <section aria-labelledby="team-coverage-heading">
      <div className="operations-section-heading">
        <div><h2 id="team-coverage-heading">Team coverage</h2><p>Assignment coverage at the displayed time; staffing targets are not yet available.</p></div>
        {canCorrectTeams && <button className="operations-link-button" onClick={() => onNavigate('teams')}>Manage teams</button>}
      </div>
      {!canCorrectTeams && (
        <p className="operations-read-only">Team membership and leadership are read-only for your account. Ask an Administrator or Company Owner to make corrections.</p>
      )}
      {teams.length === 0 ? (
        <div className="operations-empty"><strong>No Teams found.</strong><p>Create and manage Teams from the Teams page if you have permission.</p></div>
      ) : (
        <div className="operations-team-grid">
          {teams.map((team) => (
            <article className="operations-team" key={team.id}>
              <div className="operations-team-title">
                <h3>{team.name}</h3>
                <span className={`operations-status operations-status--${team.status}`}>{team.status}</span>
              </div>
              <dl>
                <div><dt>Active members</dt><dd>{team.active_member_count}</dd></div>
                <div><dt>Available now</dt><dd>{team.available_member_count}</dd></div>
                <div><dt>Deployed now</dt><dd>{team.deployed_member_count}</dd></div>
                <div><dt>Team leader</dt><dd>{team.leader_name || 'No leader assigned'}</dd></div>
              </dl>
              <p><strong>Current deployment:</strong> {team.current_patrols.length ? team.current_patrols.join(', ') : 'No current deployment'}</p>
              <p><strong>Staffing target:</strong> Unavailable</p>
              {team.attention.map((warning) => <p className="operations-warning" key={warning}>Attention: {warning}</p>)}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
