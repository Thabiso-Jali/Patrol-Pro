import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { loadOperationsWorkspace } from './api';
import OperationsActions from './OperationsActions';
import OperationsFilters from './OperationsFilters';
import OperationsSummary from './OperationsSummary';
import StaffAvailabilityList from './StaffAvailabilityList';
import TeamCoverageList from './TeamCoverageList';
import { canManageTeams } from './permissions';
import { activeFilterLabels, DEFAULT_FILTERS, filterStaff } from './selectors';
import './operations.css';

export default function OperationsWorkspacePage({ apiCall, permissions, onNavigate }) {
  const apiCallRef = useRef(apiCall);
  apiCallRef.current = apiCall;
  const mountedRef = useRef(true);
  const requestInFlightRef = useRef(false);
  const [state, setState] = useState({ loading: true, data: null, error: '' });
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const load = useCallback(async () => {
    if (requestInFlightRef.current) return;
    requestInFlightRef.current = true;
    setState((current) => ({ ...current, loading: true, error: '' }));
    try {
      const result = await loadOperationsWorkspace(apiCallRef.current);
      if (!mountedRef.current) return;
      if (result.ok) setState({ loading: false, data: result.data, error: '' });
      else setState({ loading: false, data: null, error: 'Operations staffing is unavailable.' });
    } finally {
      requestInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    load();
    return () => { mountedRef.current = false; };
  }, [load]);

  const filteredStaff = useMemo(
    () => filterStaff(state.data?.staff || [], filters),
    [state.data, filters],
  );
  const filterLabels = activeFilterLabels(filters, state.data?.teams || []);

  if (state.loading) return <div className="operations-state" role="status">Loading the current staffing snapshot…</div>;
  if (state.error) return (
    <div className="operations-state operations-state--error" role="alert">
      <h1>Operations Workspace</h1><p>{state.error} No operational figures are being shown.</p>
      <button onClick={load}>Retry</button>
    </div>
  );

  const { data } = state;
  return (
    <div className="operations-workspace">
      <header className="operations-header">
        <div><p className="operations-eyebrow">Daily operations</p><h1>Operations Workspace</h1><p>Understand current staffing and Team coverage from one read-only snapshot.</p></div>
        <div className="operations-refresh"><span>As of {new Date(data.as_of).toLocaleString()}</span><button onClick={load}>Refresh</button></div>
      </header>
      <OperationsSummary metrics={data.metrics} />
      <p className="operations-definition">{data.availability_definition}</p>
      <OperationsActions onNavigate={onNavigate} permissions={permissions} />
      <OperationsFilters filters={filters} setFilters={setFilters} teams={data.teams} resultCount={filteredStaff.length} />
      <StaffAvailabilityList
        staff={filteredStaff}
        emptyDetail={filterLabels.length ? `Active filters: ${filterLabels.join(', ')}.` : 'No operational workforce records exist for this organisation.'}
      />
      <TeamCoverageList teams={data.teams} onNavigate={onNavigate} canCorrectTeams={canManageTeams(permissions)} />
    </div>
  );
}
