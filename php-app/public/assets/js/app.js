const api = async (path, options = {}) => {
  const response = await fetch(`/api${path}`, {
    credentials: 'same-origin',
    headers: options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
};

const $ = (id) => document.getElementById(id);
const state = {
  user: null,
  patrols: [],
  guards: [],
  incidents: [],
  shifts: [],
  notifications: [],
  incidentPage: 1,
  incidentSort: 'reported_at',
  charts: {},
  review: null,
};

const roleViews = {
  Admin: ['dashboard', 'patrols', 'guards', 'incidents', 'monitoring', 'shifts', 'reports', 'client'],
  Supervisor: ['dashboard', 'patrols', 'incidents', 'monitoring', 'shifts', 'reports'],
  Guard: ['dashboard', 'patrols', 'incidents', 'shifts'],
  Client: ['dashboard', 'incidents', 'reports', 'client'],
};

const roleCopy = {
  Admin: 'Full platform administration',
  Supervisor: 'Operations supervision',
  Guard: 'Assigned patrol workflow',
  Client: 'Read-only client portal',
};

const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
}[char]));

function toast(message, type = 'info') {
  const node = $('toast');
  node.textContent = message;
  node.dataset.type = type;
  node.classList.add('show');
  setTimeout(() => node.classList.remove('show'), 3000);
}

function setView(name, silent = false) {
  const allowed = roleViews[state.user?.role] || ['dashboard'];
  if (!allowed.includes(name)) {
    if (!silent) toast('This page is not available for your role', 'warning');
    return false;
  }
  document.querySelectorAll('.view').forEach((view) => view.classList.toggle('active', view.id === name));
  document.querySelectorAll('.nav').forEach((nav) => nav.classList.toggle('active', nav.dataset.view === name));
  const titles = {
    dashboard: ['Dashboard', 'Live operational overview'],
    patrols: ['Patrol Management', 'Routes, checkpoints and completion'],
    guards: ['Guard Management', 'Profiles, status and compliance'],
    incidents: ['Incident Reporting', 'Evidence, categories and case status'],
    monitoring: ['Live Monitoring', 'Guard status, map placeholder and progress'],
    shifts: ['Shift Management', 'Calendar-style assignments'],
    reports: ['Reporting', 'Daily summaries and PDF export'],
    client: ['Client Portal', 'Restricted read-only customer view'],
  };
  $('pageTitle').textContent = titles[name][0];
  $('pageSubtitle').textContent = titles[name][1];
  document.querySelector('.sidebar').classList.remove('open');
  return true;
}

function applyRoleAccess() {
  const role = state.user?.role || 'Client';
  const allowed = roleViews[role] || ['dashboard'];
  document.querySelectorAll('.nav').forEach((nav) => { nav.hidden = !allowed.includes(nav.dataset.view); });
  document.querySelectorAll('.view').forEach((view) => { view.hidden = !allowed.includes(view.id); });
  document.querySelectorAll('[data-modal="guardModal"]').forEach((button) => { button.hidden = role !== 'Admin'; });
  document.querySelectorAll('[data-modal="patrolModal"]').forEach((button) => { button.hidden = !['Admin', 'Supervisor'].includes(role); });
  document.querySelectorAll('[data-modal="shiftModal"]').forEach((button) => { button.hidden = !['Admin', 'Supervisor'].includes(role); });
  document.querySelectorAll('[data-modal="incidentModal"]').forEach((button) => { button.hidden = role === 'Client'; });
  $('pageSubtitle').textContent = roleCopy[role] || 'Role-based workspace';
  setView(allowed[0], true);
}

function applySidebarState() {
  const collapsed = localStorage.getItem('patrolProSidebarCollapsed') === 'true';
  $('appView')?.classList.toggle('sidebar-collapsed', collapsed);
  if ($('sidebarToggle')) {
    $('sidebarToggle').textContent = collapsed ? '›' : '‹';
    $('sidebarToggle').setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    $('sidebarToggle').setAttribute('aria-expanded', String(!collapsed));
  }
}

function toggleSidebarCollapsed() {
  const app = $('appView');
  const collapsed = !app.classList.contains('sidebar-collapsed');
  app.classList.toggle('sidebar-collapsed', collapsed);
  localStorage.setItem('patrolProSidebarCollapsed', String(collapsed));
  applySidebarState();
  setTimeout(renderCharts, 220);
}

function statusBadge(value) {
  const normalized = String(value || 'open').toLowerCase();
  return `<span class="status-badge status-${esc(normalized)}">${esc(value)}</span>`;
}

function priorityBadge(value) {
  const normalized = String(value || 'medium').toLowerCase();
  return `<span class="priority-badge priority-${esc(normalized)}">${esc(value)}</span>`;
}

function canUseModal(modal) {
  const role = state.user?.role;
  const restricted = {
    guardModal: ['Admin'],
    patrolModal: ['Admin', 'Supervisor'],
    shiftModal: ['Admin', 'Supervisor'],
    incidentModal: ['Admin', 'Supervisor', 'Guard'],
  };
  return Boolean(restricted[modal]?.includes(role));
}

function canDeleteEntity(entity) {
  const role = state.user?.role;
  return {
    guards: ['Admin'],
    patrols: ['Admin', 'Supervisor'],
    incidents: ['Admin', 'Supervisor'],
    shifts: ['Admin', 'Supervisor'],
  }[entity]?.includes(role) || false;
}

function emptyState(title, action, modal) {
  return `<div class="feed-item"><div class="avatar">◇</div><div><p class="feed-title">${esc(title)}</p><p class="feed-meta">Nothing needs attention here yet.</p></div>${modal && canUseModal(modal) ? `<button class="btn ghost" data-modal="${modal}">${esc(action)}</button>` : ''}</div>`;
}

function enterpriseTable({ columns, rows, emptyTitle, emptyAction, emptyModal, entity, actions }) {
  if (!rows.length) return emptyState(emptyTitle, emptyAction, emptyModal);
  const actionButtons = (row, index) => {
    const custom = actions ? actions(row, index) : '';
    return `${custom}<button class="btn ghost" data-review-entity="${esc(entity)}" data-review-index="${index}">Review</button>`;
  };
  return `<table><thead><tr>${columns.map((h) => `<th data-sort="${esc(h.key)}">${esc(h.label)}</th>`).join('')}<th>Actions</th></tr></thead><tbody>${
    rows.map((row, index) => `<tr>${columns.map((h) => `<td>${h.render ? h.render(row) : esc(row[h.key])}</td>`).join('')}<td><div class="table-actions">${actionButtons(row, index)}</div></td></tr>`).join('')
  }</tbody></table>`;
}

function reviewRowsForEntity(entity) {
  if (entity === 'incidents') return filteredIncidents();
  return {
    patrols: state.patrols,
    guards: state.guards,
    shifts: state.shifts,
  }[entity] || [];
}

function openReview(entity, index) {
  const row = reviewRowsForEntity(entity)[Number(index)];
  if (!row) return toast('Record could not be opened', 'error');
  state.review = { entity, row };
  const id = row.id || row.incident_id || row.shift_id;
  $('reviewTitle').textContent = `Review ${entity.slice(0, -1)}`;
  $('reviewSubtitle').textContent = id ? `Record ${id}` : 'Record details';
  $('deleteReviewBtn').hidden = !canDeleteEntity(entity);
  $('deleteReviewBtn').textContent = entity === 'patrols' ? 'Archive route' : entity === 'guards' ? 'Deactivate guard' : 'Delete';
  $('reviewDetails').innerHTML = Object.entries(row)
    .filter(([key]) => !['checkpoints', 'password_hash'].includes(key))
    .map(([key, value]) => `<div class="review-field"><span>${esc(key.replaceAll('_', ' '))}</span><strong>${esc(value === null || value === '' ? 'Not set' : value)}</strong></div>`)
    .join('');
  $('reviewModal').showModal();
}

async function deleteReviewedRecord() {
  if (!state.review) return;
  const { entity, row } = state.review;
  if (!canDeleteEntity(entity)) return toast('Delete is not available for your role', 'warning');
  const id = row.id || String(row.incident_id || '').replace('INC-', '');
  if (!id) return toast('Record id is missing', 'error');
  const label = entity === 'patrols' ? 'archive this route' : entity === 'guards' ? 'deactivate this guard' : 'delete this record';
  if (!confirm(`Are you sure you want to ${label}?`)) return;
  await api(`/${entity}?id=${encodeURIComponent(id)}`, { method: 'DELETE' });
  $('reviewModal').close();
  toast(entity === 'patrols' ? 'Route archived' : entity === 'guards' ? 'Guard deactivated' : 'Record deleted', 'success');
  if (entity === 'patrols') await loadPatrols();
  if (entity === 'guards') await loadGuards();
  if (entity === 'incidents') await loadIncidents();
  if (entity === 'shifts') await loadShifts();
  await loadDashboard();
}

function renderKpis(data) {
  const items = [
    ['Guards', data.total_guards ?? 0, '◉', 'Live', 'up', 'From users table'],
    ['Active Patrols', data.active_patrols ?? 0, '◎', 'Live', 'up', 'From patrol routes'],
    ['Open Incidents', data.open_incidents ?? 0, '△', 'Live', 'up', 'From incidents'],
    ['Completed Shifts', data.completed_shifts ?? 0, '◷', 'Live', 'up', 'From shifts'],
  ];
  $('kpiGrid').innerHTML = items.map(([title, value, icon, trend, direction, meta]) => `
    <article class="kpi">
      <div class="kpi-top"><div><div class="kpi-title">${esc(title)}</div><strong>${esc(value)}</strong></div><div class="kpi-icon">${esc(icon)}</div></div>
      <div class="kpi-meta"><span class="trend ${direction}">${esc(trend)}</span><span>${esc(meta)}</span></div>
    </article>
  `).join('');
}

function renderActivity(items = []) {
  if (!items.length) {
    $('activityFeed').innerHTML = emptyState('No activity has been logged yet.', '', null);
    return;
  }
  $('activityFeed').innerHTML = items.map(([avatar, title, body, time, tone, priority]) => `
    <div class="feed-item">
      <div class="avatar">${esc(avatar)}</div>
      <div><p class="feed-title">${esc(title)}</p><p class="feed-meta">${esc(body)}</p></div>
      <div><span class="status-badge status-${tone === 'error' ? 'open' : 'completed'}">${esc(priority)}</span><p class="feed-meta">${esc(time)}</p></div>
    </div>
  `).join('');
}

function renderQuickActions() {
  const role = state.user?.role;
  const actions = [
    ['◎', 'Patrols', 'view', 'patrols'],
    ['△', 'Incidents', 'view', 'incidents'],
    ['▤', 'Reports', 'view', 'reports'],
    ['◇', 'Client Portal', 'view', 'client'],
    ['+', 'Add Guard', 'modal', 'guardModal'],
    ['+', 'New Route', 'modal', 'patrolModal'],
    ['+', 'Assign Shift', 'modal', 'shiftModal'],
    ['+', 'Report Incident', 'modal', 'incidentModal'],
  ].filter(([, , type, target]) => {
    if (type === 'view') return (roleViews[role] || []).includes(target);
    return canUseModal(target);
  });
  $('quickActions').innerHTML = actions.map(([icon, label, type, target]) => `
    <button class="quick-action" type="button" ${type === 'view' ? `data-view-shortcut="${target}"` : `data-modal="${target}"`}>
      <span>${esc(icon)}</span>${esc(label)}
    </button>
  `).join('');
}

function renderMapMarkers() {
  const patrolMarkers = state.patrols.map((patrol, index) => {
    const left = 18 + ((index * 23) % 64);
    const top = 24 + ((index * 17) % 52);
    return `<span class="map-marker" title="${esc(patrol.name)}" style="left:${left}%;top:${top}%"></span>`;
  });
  const incidentMarkers = state.incidents.map((incident, index) => {
    const left = 28 + ((index * 29) % 54);
    const top = 20 + ((index * 19) % 56);
    return `<span class="map-marker alert" title="${esc(incident.title)}" style="left:${left}%;top:${top}%"></span>`;
  });
  const markers = `${patrolMarkers.join('')}${incidentMarkers.join('')}`;
  if ($('mapMarkers')) $('mapMarkers').innerHTML = markers;
  if ($('dashboardMapMarkers')) $('dashboardMapMarkers').innerHTML = markers;
  $('mapCallout').textContent = `${state.patrols.length} patrol route${state.patrols.length === 1 ? '' : 's'} · ${state.incidents.length} incident${state.incidents.length === 1 ? '' : 's'}`;
}

function renderCharts() {
  if (!window.Chart) return;
  const chartColor = getComputedStyle(document.body).getPropertyValue('--pink-dark').trim();
  const textColor = getComputedStyle(document.body).getPropertyValue('--muted').trim();
  const incidentCounts = state.incidents.reduce((totals, incident) => {
    const day = incident.reported_at ? new Date(incident.reported_at).toLocaleDateString([], { weekday: 'short' }) : 'Unk';
    totals[day] = (totals[day] || 0) + 1;
    return totals;
  }, {});
  const categoryCounts = state.incidents.reduce((totals, incident) => {
    const category = incident.category || 'Uncategorised';
    totals[category] = (totals[category] || 0) + 1;
    return totals;
  }, {});
  const totalCheckpoints = state.patrols.reduce((sum, patrol) => sum + Number(patrol.checkpoint_count || 0), 0);
  const completedCheckpoints = state.patrols.reduce((sum, patrol) => sum + Number(patrol.completed_count || 0), 0);
  const remainingCheckpoints = Math.max(totalCheckpoints - completedCheckpoints, 0);
  Object.values(state.charts).forEach((chart) => chart.destroy());
  state.charts.trend = new Chart($('incidentTrendChart'), {
    type: 'line',
    data: { labels: Object.keys(incidentCounts).length ? Object.keys(incidentCounts) : ['No incidents'], datasets: [{ label: 'Incidents', data: Object.values(incidentCounts).length ? Object.values(incidentCounts) : [0], borderColor: chartColor, backgroundColor: 'rgba(244,114,182,.16)', tension: .38, fill: true }] },
    options: chartOptions(textColor),
  });
  state.charts.completion = new Chart($('patrolCompletionChart'), {
    type: 'doughnut',
    data: { labels: ['Completed checkpoints', 'Remaining checkpoints'], datasets: [{ data: totalCheckpoints ? [completedCheckpoints, remainingCheckpoints] : [0, 1], backgroundColor: [chartColor, '#e2e8f0'], borderWidth: 0 }] },
    options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { color: textColor } } }, cutout: '72%' },
  });
  state.charts.categories = new Chart($('incidentCategoryChart'), {
    type: 'bar',
    data: { labels: Object.keys(categoryCounts).length ? Object.keys(categoryCounts) : ['No incidents'], datasets: [{ label: 'Cases', data: Object.values(categoryCounts).length ? Object.values(categoryCounts) : [0], backgroundColor: ['#dc2626', '#f97316', '#facc15', '#16a34a'], borderRadius: 9 }] },
    options: chartOptions(textColor),
  });
}

function chartOptions(textColor) {
  return {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: textColor }, grid: { display: false } },
      y: { ticks: { color: textColor }, grid: { color: 'rgba(148,163,184,.2)' } },
    },
  };
}

async function loadDashboard() {
  const { data } = await api('/dashboard');
  renderKpis(data);
  renderActivity(data.activity?.map((item) => ['PP', item.action, `${item.entity_type} ${item.detail || ''}`, item.created_at, 'info', 'Logged']) || []);
  renderQuickActions();
  renderMapMarkers();
  setTimeout(renderCharts, 80);
}

async function loadPatrols() {
  const { data } = await api('/patrols');
  state.patrols = data;
  $('patrolTable').classList.remove('skeleton');
  $('patrolTable').innerHTML = enterpriseTable({
    columns: [
      { key: 'id', label: 'ID' },
      { key: 'name', label: 'Route' },
      { key: 'site_name', label: 'Site' },
      { key: 'status', label: 'Status', render: (row) => statusBadge(row.status) },
      { key: 'checkpoint_count', label: 'Checkpoints' },
      { key: 'completed_count', label: 'Completed' },
    ],
    rows: data,
    emptyTitle: 'No patrols are currently scheduled.',
    emptyAction: 'Create Patrol',
    emptyModal: 'patrolModal',
    entity: 'patrols',
  });
  renderClientPortal();
}

async function loadGuards() {
  const query = $('guardSearch')?.value ? `?search=${encodeURIComponent($('guardSearch').value)}` : '';
  const { data } = await api(`/guards${query}`);
  state.guards = data;
  renderGuardCards();
  $('guardTable').classList.remove('skeleton');
  $('guardTable').innerHTML = enterpriseTable({
    columns: [
      { key: 'id', label: 'ID' },
      { key: 'name', label: 'Name' },
      { key: 'email', label: 'Email' },
      { key: 'badge_number', label: 'Badge' },
      { key: 'certification', label: 'Certification' },
      { key: 'status', label: 'Status', render: (row) => statusBadge(row.status) },
    ],
    rows: state.guards,
    emptyTitle: 'No guards match this filter.',
    emptyAction: 'Add Guard',
    emptyModal: 'guardModal',
    entity: 'guards',
  });
}

function renderGuardCards() {
  if (!state.guards.length) {
    $('guardCards').innerHTML = emptyState('No guards have been added yet.', 'Add Guard', 'guardModal');
    $('guardStatus').innerHTML = emptyState('No guard status is available yet.', 'Add Guard', 'guardModal');
    return;
  }
  const cards = state.guards.map((guard) => {
    const initials = String(guard.name || 'Guard').split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase();
    return `<article class="guard-card">
      <div class="guard-card-head"><div class="guard-photo">${esc(initials)}</div><div><strong>${esc(guard.name)}</strong><p class="feed-meta">${esc(guard.badge_number || 'No badge assigned')}</p></div>${guard.status === 'active' ? '<span class="pill success">Active</span>' : '<span class="pill">Inactive</span>'}</div>
      <div class="signal-row"><span>Email</span><strong>${esc(guard.email)}</strong></div>
      <div class="signal-row"><span>Phone</span><strong>${esc(guard.phone || 'Not set')}</strong></div>
      <div class="signal-row"><span>Certification</span><strong>${esc(guard.certification || 'Not set')}</strong></div>
    </article>`;
  }).join('');
  $('guardCards').innerHTML = cards;
  $('guardStatus').innerHTML = cards;
}

function filteredIncidents() {
  const search = ($('incidentSearch')?.value || '').toLowerCase();
  const priority = $('incidentPriorityFilter')?.value || '';
  const status = $('incidentStatusFilter')?.value || '';
  const rows = state.incidents.map((incident, index) => ({
    incident_id: `INC-${String(incident.id || index + 1).padStart(5, '0')}`,
    id: incident.id,
    priority: incident.severity || 'medium',
    location: incident.site_name || 'Not assigned',
    assigned_guard: incident.guard_name || 'Unassigned',
    status: incident.status || 'open',
    time: incident.reported_at || 'Not set',
    title: incident.title || 'Untitled incident',
    category: incident.category || 'Uncategorised',
  }));
  return rows.filter((row) => {
    const haystack = Object.values(row).join(' ').toLowerCase();
    return (!search || haystack.includes(search)) && (!priority || row.priority === priority) && (!status || row.status === status);
  });
}

async function loadIncidents() {
  const { data } = await api('/incidents');
  state.incidents = data;
  renderIncidentTable();
  renderClientPortal();
}

function renderIncidentTable() {
  const rows = filteredIncidents();
  $('incidentTable').classList.remove('skeleton');
  $('incidentTable').innerHTML = enterpriseTable({
    columns: [
      { key: 'incident_id', label: 'Incident ID' },
      { key: 'priority', label: 'Priority', render: (row) => priorityBadge(row.priority) },
      { key: 'location', label: 'Location' },
      { key: 'assigned_guard', label: 'Assigned Guard' },
      { key: 'status', label: 'Status', render: (row) => statusBadge(row.status) },
      { key: 'time', label: 'Time' },
    ],
    rows,
    emptyTitle: 'No incidents match your filters.',
    emptyAction: 'Report Incident',
    emptyModal: 'incidentModal',
    entity: 'incidents',
  });
}

async function loadShifts() {
  const { data } = await api('/shifts');
  state.shifts = data;
  $('shiftTable').classList.remove('skeleton');
  $('shiftTable').innerHTML = enterpriseTable({
    columns: [
      { key: 'guard_name', label: 'Guard' },
      { key: 'route_name', label: 'Route' },
      { key: 'starts_at', label: 'Starts' },
      { key: 'ends_at', label: 'Ends' },
      { key: 'status', label: 'Status', render: (row) => statusBadge(row.status) },
    ],
    rows: data,
    emptyTitle: 'No shifts are currently scheduled.',
    emptyAction: 'Assign Shift',
    emptyModal: 'shiftModal',
    entity: 'shifts',
    actions: (row) => {
      if (row.status === 'scheduled') {
        return `<button class="btn secondary" data-shift-action="start" data-shift-id="${esc(row.id)}">Start Shift</button>`;
      }
      if (row.status === 'active') {
        return `<button class="btn primary" data-shift-action="clock-out" data-shift-id="${esc(row.id)}">Clock Out</button>`;
      }
      return '';
    },
  });
}

async function updateShiftStatus(id, action) {
  if (!id || !['start', 'clock-out'].includes(action)) {
    toast('Shift action is not available', 'error');
    return;
  }
  const label = action === 'start' ? 'Shift started' : 'Clocked out';
  await api(`/shifts/${action}`, { method: 'POST', body: JSON.stringify({ id }) });
  toast(label, 'success');
  await loadShifts();
  await loadDashboard();
}

async function loadReport() {
  const date = $('reportDate').value || new Date().toISOString().slice(0, 10);
  const { data } = await api(`/reports?date=${encodeURIComponent(date)}`);
  $('reportOutput').innerHTML = `<pre>${esc(JSON.stringify(data, null, 2))}</pre>`;
}

function renderClientPortal() {
  if (!$('clientPortal')) return;
  const routes = state.patrols.map((route) => `<div class="client-card"><strong>${esc(route.site_name)}</strong><p>${esc(route.name)}</p><span class="pill">${esc(route.completed_count)}/${esc(route.checkpoint_count)} checkpoints</span></div>`).join('');
  const incidents = filteredIncidents().slice(0, 6).map((incident) => `<div class="client-card"><strong>${esc(incident.title)}</strong><p>${priorityBadge(incident.priority)} ${statusBadge(incident.status)}</p><small>${esc(incident.time)}</small></div>`).join('');
  $('clientPortal').innerHTML = `${routes || '<div class="client-card">No patrol summaries available.</div>'}${incidents}`;
}

function renderNotifications() {
  $('notificationCount').textContent = state.notifications.length;
  $('notificationMenu').innerHTML = state.notifications.map((item) => `
    <div class="feed-item"><div class="avatar">${item.type === 'error' ? '!' : '✓'}</div><div><p class="feed-title">${esc(item.title)}</p><p class="feed-meta">${esc(item.body || '')}</p></div><small class="feed-meta">${esc(item.created_at || '')}</small></div>
  `).join('') || '<div class="feed-item">No unread notifications.</div>';
}

async function loadNotifications() {
  try {
    const { data } = await api('/notifications');
    state.notifications = data.filter((item) => !item.read_at);
  } catch {
    state.notifications = [];
  }
  renderNotifications();
}

function updateClock() {
  const now = new Date();
  $('dateTime').textContent = now.toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

async function loadForRole() {
  const role = state.user.role;
  const tasks = [];
  if (['Admin', 'Supervisor', 'Guard', 'Client'].includes(role)) tasks.push(loadPatrols());
  if (['Admin', 'Supervisor'].includes(role)) tasks.push(loadGuards());
  if (['Admin', 'Supervisor', 'Guard', 'Client'].includes(role)) tasks.push(loadIncidents());
  if (['Admin', 'Supervisor', 'Guard'].includes(role)) tasks.push(loadShifts());
  await Promise.all(tasks);
  await loadNotifications();
  await loadDashboard();
  if (['Admin', 'Supervisor', 'Client'].includes(role)) await loadReport();
}

async function bootstrap() {
  const { user } = await api('/me');
  if (!user) return;
  state.user = user;
  $('loginView').classList.add('hidden');
  $('appView').classList.remove('hidden');
  $('userBadge').textContent = `${user.name} · ${user.role}`;
  applyRoleAccess();
  applySidebarState();
  updateClock();
  setInterval(updateClock, 30000);
  await loadForRole();
}

function formJson(form) {
  return Object.fromEntries(new FormData(form).entries());
}

document.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    if (event.target.id === 'loginForm') {
      const { user } = await api('/login', { method: 'POST', body: JSON.stringify(formJson(event.target)) });
      state.user = user;
      toast('Signed in', 'success');
      await bootstrap();
    }
    if (event.target.id === 'guardForm') {
      await api('/guards', { method: 'POST', body: JSON.stringify(formJson(event.target)) });
      event.target.closest('dialog').close();
      toast('Guard added', 'success');
      await loadGuards();
    }
    if (event.target.id === 'patrolForm') {
      await api('/patrols', { method: 'POST', body: JSON.stringify(formJson(event.target)) });
      event.target.closest('dialog').close();
      toast('Patrol route created', 'success');
      await loadPatrols();
      await loadDashboard();
    }
    if (event.target.id === 'incidentForm') {
      await api('/incidents', { method: 'POST', body: new FormData(event.target) });
      event.target.closest('dialog').close();
      toast('Incident submitted', 'success');
      await loadNotifications();
      await loadIncidents();
      await loadDashboard();
    }
    if (event.target.id === 'shiftForm') {
      await api('/shifts', { method: 'POST', body: JSON.stringify(formJson(event.target)) });
      event.target.closest('dialog').close();
      toast('Shift assigned', 'success');
      await loadShifts();
    }
  } catch (error) {
    toast(error.message, 'error');
  }
});

document.addEventListener('click', async (event) => {
  const shiftActionButton = event.target.closest('[data-shift-action]');
  if (shiftActionButton) {
    try {
      await updateShiftStatus(shiftActionButton.dataset.shiftId, shiftActionButton.dataset.shiftAction);
    } catch (error) {
      toast(error.message, 'error');
    }
    return;
  }
  const modal = event.target.dataset?.modal;
  if (modal) {
    if (!canUseModal(modal)) return toast('This action is not available for your role', 'warning');
    $(modal).showModal();
  }
  if (event.target.matches('.nav')) setView(event.target.dataset.view);
  if (event.target.closest('[data-view-shortcut]')) setView(event.target.closest('[data-view-shortcut]').dataset.viewShortcut);
  if (event.target.dataset?.reviewEntity) openReview(event.target.dataset.reviewEntity, event.target.dataset.reviewIndex);
  if (event.target.id === 'deleteReviewBtn') {
    try {
      await deleteReviewedRecord();
    } catch (error) {
      toast(error.message, 'error');
    }
  }
  if (event.target.id === 'menuBtn') document.querySelector('.sidebar').classList.toggle('open');
  if (event.target.id === 'sidebarToggle') toggleSidebarCollapsed();
  if (event.target.matches('[data-close-modal]')) event.target.closest('dialog')?.close();
  if (event.target.id === 'darkModeBtn') {
    document.body.classList.toggle('dark');
    setTimeout(renderCharts, 50);
  }
  if (event.target.id === 'notificationBtn') $('notificationMenu').classList.toggle('hidden');
  if (event.target.id === 'logoutBtn') {
    await api('/logout', { method: 'POST', body: '{}' });
    location.reload();
  }
  if (event.target.id === 'loadReportBtn') loadReport();
  if (event.target.id === 'pdfBtn') {
    const date = $('reportDate').value || new Date().toISOString().slice(0, 10);
    window.open(`/api/reports?date=${encodeURIComponent(date)}&format=pdf`, '_blank');
  }
  if (event.target.dataset?.refresh !== undefined) loadDashboard();
});

['incidentSearch', 'incidentPriorityFilter', 'incidentStatusFilter'].forEach((id) => {
  $(id)?.addEventListener('input', renderIncidentTable);
  $(id)?.addEventListener('change', renderIncidentTable);
});
$('guardSearch')?.addEventListener('input', () => loadGuards().catch((error) => toast(error.message, 'error')));
$('globalSearch')?.addEventListener('input', (event) => {
  const query = event.target.value.toLowerCase();
  document.querySelectorAll('tbody tr, .guard-card, .client-card').forEach((row) => {
    row.hidden = query && !row.textContent.toLowerCase().includes(query);
  });
});
$('reportDate').value = new Date().toISOString().slice(0, 10);
bootstrap().catch(() => {});
