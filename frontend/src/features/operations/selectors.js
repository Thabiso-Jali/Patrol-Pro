export const DEFAULT_FILTERS = Object.freeze({
  search: '',
  availability: 'all',
  team: 'all',
  assignment: 'all',
  account: 'all',
});

export const filterStaff = (staff = [], filters = DEFAULT_FILTERS) => {
  const query = filters.search.trim().toLocaleLowerCase();
  return staff.filter((person) => {
    const identity = `${person.full_name || ''} ${person.staff_identifier}`.toLocaleLowerCase();
    if (query && !identity.includes(query)) return false;
    if (filters.availability !== 'all' && person.availability_status !== filters.availability) return false;
    if (filters.team !== 'all' && String(person.team_id || 'none') !== filters.team) return false;
    if (filters.assignment === 'assigned' && person.current_patrols.length === 0) return false;
    if (filters.assignment === 'unassigned' && person.current_patrols.length > 0) return false;
    if (filters.account !== 'all' && person.account_status !== filters.account) return false;
    return true;
  });
};

export const activeFilterLabels = (filters, teams = []) => {
  const labels = [];
  if (filters.search.trim()) labels.push(`search “${filters.search.trim()}”`);
  if (filters.availability !== 'all') labels.push(filters.availability);
  if (filters.team !== 'all') {
    labels.push(filters.team === 'none'
      ? 'without a team'
      : `team ${teams.find((team) => String(team.id) === filters.team)?.name || filters.team}`);
  }
  if (filters.assignment !== 'all') labels.push(`${filters.assignment} to a current patrol`);
  if (filters.account !== 'all') labels.push(`${filters.account} accounts`);
  return labels;
};
