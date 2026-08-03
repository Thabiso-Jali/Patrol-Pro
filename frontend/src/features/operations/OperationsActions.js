import React from 'react';
import { canManagePatrols, canManageWorkforce } from './permissions';

export default function OperationsActions({ onNavigate, permissions }) {
  const showPatrolAction = canManagePatrols(permissions);
  const showWorkforceAction = canManageWorkforce(permissions);
  return (
    <div className="operations-actions" aria-label="Corrective actions">
      {showPatrolAction && <button onClick={() => onNavigate('patrols')}>Review patrol assignments</button>}
      {showWorkforceAction && <button onClick={() => onNavigate('officers')}>Review workforce accounts</button>}
      {!showPatrolAction && !showWorkforceAction && (
        <p>This workspace is read-only. Ask an authorised manager to correct assignments or workforce records.</p>
      )}
    </div>
  );
}
