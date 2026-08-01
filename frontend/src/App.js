import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { lightTokens, darkTokens, spacing, radius, typography, shadows, transitions } from './theme';
import { API_BASE_URL } from './apiConfig';
import { canAccessPage, visibleNavigation } from './rbac';
import CustomersPage from './features/customers/CustomersPage';
import ReportsPage from './features/reports/ReportsPage';
import SettingsPage from './features/settings/SettingsPage';

const API_BASE = API_BASE_URL;

export const CHECKPOINT_CONFIRMATION_COPY = Object.freeze({
  action: 'Confirm Checkpoint Code',
  accepted: 'Checkpoint code accepted',
  assurance: 'Low-assurance manual confirmation',
});

export const checkpointStatusLabel = (status) => (
  status === 'verified' ? 'Code accepted' : status
);

// ==================== THEME CONTEXT ====================
const ThemeContext = createContext({ dark: false, toggle: () => {}, colors: lightTokens });
const useTheme = () => useContext(ThemeContext);

function ThemeProvider({ children }) {
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('pp_dark') === 'true'; } catch { return false; }
  });
  const toggle = useCallback(() => {
    setDark((d) => {
      const next = !d;
      try { localStorage.setItem('pp_dark', String(next)); } catch {}
      return next;
    });
  }, []);
  const colors = dark ? darkTokens : lightTokens;
  return <ThemeContext.Provider value={{ dark, toggle, colors }}>{children}</ThemeContext.Provider>;
}

// ==================== ICON COMPONENTS ====================
const Icon = ({ name, size = 20, color }) => {
  const { colors } = useTheme();
  const resolvedColor = color || colors.slate700;
  const icons = {
    dashboard: '📊', patrols: '🚶', officers: '👮', incidents: '⚠️',
    checkpoints: '📍', reports: '📋', analytics: '📈', vehicles: '🚗',
    customers: '🏢', users: '👥', settings: '⚙️',
    home: '🏠', menu: '☰', x: '✕', search: '🔍', bell: '🔔',
    user: '👤', logout: '🚪', add: '➕', edit: '✏️', trash: '🗑️',
    check: '✓', clock: '⏱️', alertTriangle: '△', checkCircle: '✓◯',
    arrowRight: '→', filter: '⊞', download: '⬇', calendar: '📅',
    send: '⬆', load: '↻', success: '✓',
  };
  return <span style={{ fontSize: size, display: 'inline-block', opacity: 0.85, color: resolvedColor }}>{icons[name] || name}</span>;
};

// ==================== REUSABLE COMPONENTS ====================

const Skeleton = ({ width = '100%', height = 20, borderRadius = 6, style = {} }) => {
  const { colors } = useTheme();
  return (
    <div style={{
      width,
      height,
      borderRadius,
      background: `linear-gradient(90deg, ${colors.skeletonBase} 25%, ${colors.skeletonHighlight} 50%, ${colors.skeletonBase} 75%)`,
      backgroundSize: '200% 100%',
      animation: 'skeletonShimmer 1.4s infinite',
      ...style,
    }} />
  );
};

const SkeletonCard = () => {
  const { colors } = useTheme();
  return (
    <div className="pp-skeleton-card" style={{ background: colors.cardBg, borderRadius: 'var(--pp-card-radius)', padding: 'var(--pp-card-padding)', border: `1px solid ${colors.border}` }}>
      <Skeleton height={18} width='60%' style={{ marginBottom: spacing.sm }} />
      <Skeleton height={14} width='80%' style={{ marginBottom: spacing.md }} />
      <Skeleton height={14} width='40%' />
    </div>
  );
};

const SkeletonTable = ({ rows = 5, cols = 4 }) => {
  const { colors } = useTheme();
  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ padding: spacing.md, background: colors.lightGrey, borderRadius: radius.sm, marginBottom: 2 }}>
        <div style={{ display: 'flex', gap: spacing.lg }}>
          {Array.from({ length: cols }).map((_, i) => <Skeleton key={i} height={14} width={80} />)}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ display: 'flex', gap: spacing.lg, padding: spacing.md, borderBottom: `1px solid ${colors.border}` }}>
          {Array.from({ length: cols }).map((_, j) => <Skeleton key={j} height={14} width={`${60 + (j * 20) % 40}%`} />)}
        </div>
      ))}
    </div>
  );
};

const Button = ({ children, variant = 'primary', size = 'md', disabled = false, icon, fullWidth = false, className = '', ...props }) => {
  const { colors } = useTheme();
  const sizeStyles = {
    sm: { padding: `${spacing.xs} ${spacing.sm}`, ...typography.labelSm },
    md: { padding: `${spacing.sm} ${spacing.md}`, ...typography.labelMd },
    lg: { padding: `${spacing.md} ${spacing.lg}`, ...typography.headingXs },
  };

  const variants = {
    primary: { background: colors.rosePink, color: '#fff', border: `1px solid ${colors.rosePink}` },
    secondary: { background: colors.lightGrey, color: colors.slate700, border: `1px solid ${colors.border}` },
    ghost: { background: 'transparent', color: colors.slate700, border: `1px solid ${colors.border}` },
    danger: { background: colors.error, color: '#fff', border: `1px solid ${colors.error}` },
  };

  const style = {
    ...sizeStyles[size],
    ...variants[variant],
    borderRadius: radius.md,
    border: '1px solid transparent',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: transitions.fast,
    fontWeight: 600,
    display: 'inline-flex',
    alignItems: 'center',
    gap: spacing.sm,
    width: fullWidth ? '100%' : 'auto',
    justifyContent: 'center',
  };

  return (
    <button className={`pp-button ${className}`.trim()} style={style} disabled={disabled} {...props}>
      {icon && <Icon name={icon} size={16} />}
      {children}
    </button>
  );
};

const Card = ({ children, header, actions, highlight = false }) => {
  const { colors } = useTheme();
  return (
    <div className="pp-card" style={{
      background: colors.white,
      borderRadius: 'var(--pp-card-radius)',
      padding: 'var(--pp-card-padding)',
      boxShadow: highlight ? shadows.md : shadows.xs,
      border: `1px solid ${colors.border}`,
      transition: transitions.base,
    }}>
      {header && (
        <div className="pp-card-header" style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'var(--pp-card-header-align)',
          marginBottom: spacing.md,
          paddingBottom: spacing.md,
          borderBottom: `1px solid ${colors.border}`,
        }}>
          <h3 style={{ ...typography.headingSm, margin: 0, color: colors.slate900 }}>{header}</h3>
          {actions && <div className="pp-card-actions" style={{ display: 'flex', gap: spacing.sm }}>{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
};

const Badge = ({ children, variant = 'default', icon }) => {
  const { colors } = useTheme();
  const variants = {
    default: { bg: colors.slate100, text: colors.slate700 },
    success: { bg: '#DCFCE7', text: '#166534' },
    warning: { bg: '#FEF3C7', text: '#92400E' },
    error: { bg: '#FEE2E2', text: '#991B1B' },
    info: { bg: '#DBEAFE', text: '#1E40AF' },
    pink: { bg: '#FCE7F3', text: '#BE123C' },
  };

  const v = variants[variant];
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: spacing.xs,
      background: v.bg,
      color: v.text,
      padding: `${spacing.xs} ${spacing.sm}`,
      borderRadius: radius.md,
      ...typography.labelSm,
      fontWeight: 600,
    }}>
      {icon && <Icon name={icon} size={14} />}
      {children}
    </span>
  );
};

const TextField = ({ label, value, onChange, type = 'text', error, placeholder, autoFocus = false }) => {
  const { colors } = useTheme();
  const inputRef = useRef(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  // Ensure value is always a string to avoid React warnings
  const safeValue = value === null || value === undefined ? '' : String(value);

  return (
    <div style={{ marginBottom: spacing.md }}>
      {label && <label style={{ ...typography.labelMd, color: colors.slate700, display: 'block', marginBottom: spacing.sm }}>{label}</label>}
      <input
        ref={inputRef}
        type={type}
        value={safeValue}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pp-field"
        style={{
          width: '100%',
          padding: spacing.md,
          border: `1px solid ${error ? colors.error : colors.border}`,
          borderRadius: radius.md,
          ...typography.bodyMd,
          boxSizing: 'border-box',
          transition: transitions.fast,
          outline: 'none',
          background: colors.cardBg,
          color: colors.slate900,
        }}
        onFocus={(e) => e.target.style.borderColor = colors.rosePink}
        onBlur={(e) => e.target.style.borderColor = colors.border}
      />
      {error && <p style={{ ...typography.bodySm, color: colors.error, marginTop: spacing.xs }}>{error}</p>}
    </div>
  );
};

const SelectField = ({ label, value, onChange, options = [], placeholder = 'Select...' }) => {
  const { colors } = useTheme();
  return (
    <div style={{ marginBottom: spacing.md }}>
      {label && <label style={{ ...typography.labelMd, color: colors.slate700, display: 'block', marginBottom: spacing.sm }}>{label}</label>}
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="pp-field"
        style={{
          width: '100%',
          padding: spacing.md,
          border: `1px solid ${colors.border}`,
          borderRadius: radius.md,
          ...typography.bodyMd,
          boxSizing: 'border-box',
          background: colors.cardBg,
          color: colors.slate900,
          outline: 'none',
          cursor: 'pointer',
        }}
      >
        <option value=''>{placeholder}</option>
        {options.map(({ value: v, label: l }) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );
};

export const SearchableMultiSelect = ({
  label,
  options = [],
  selected = [],
  onChange,
  emptyMessage = 'No available options',
}) => {
  const { colors } = useTheme();
  const [query, setQuery] = useState('');
  const filtered = options.filter((option) => (
    option.label.toLowerCase().includes(query.trim().toLowerCase())
  ));
  const toggle = (value) => {
    onChange(
      selected.includes(value)
        ? selected.filter((item) => item !== value)
        : [...selected, value]
    );
  };
  return (
    <div style={{ marginBottom: spacing.md }}>
      <label style={{ ...typography.labelMd, color: colors.slate700, display: 'block', marginBottom: spacing.sm }}>
        {label}
      </label>
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        aria-label={`Search ${label}`}
        placeholder="Search by name or staff ID"
        className="pp-field"
        style={{ width: '100%', padding: spacing.md, boxSizing: 'border-box', marginBottom: spacing.sm }}
      />
      <div style={{ border: `1px solid ${colors.border}`, borderRadius: radius.md, maxHeight: 190, overflowY: 'auto' }}>
        {filtered.length === 0 ? (
          <p style={{ ...typography.bodySm, color: colors.slate500, padding: spacing.md, margin: 0 }}>{emptyMessage}</p>
        ) : filtered.map((option) => (
          <label key={option.value} style={{ display: 'flex', gap: spacing.sm, padding: spacing.sm, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={selected.includes(option.value)}
              onChange={() => toggle(option.value)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </div>
  );
};

const TEMPORARY_PATROL_LENGTH_HOURS = 8;

const toLocalDateTimeValue = (date) => {
  const pad = (value) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

export const getDefaultPatrolSchedule = (now = new Date()) => {
  const start = new Date(now);
  start.setSeconds(0, 0);
  start.setMinutes(Math.ceil(start.getMinutes() / 15) * 15);
  if (start <= now) start.setMinutes(start.getMinutes() + 15);
  const end = new Date(start.getTime() + TEMPORARY_PATROL_LENGTH_HOURS * 60 * 60 * 1000);
  return {
    start_time: toLocalDateTimeValue(start),
    end_time: toLocalDateTimeValue(end),
  };
};

export const staffingCoverage = (form, availability) => {
  const allTeams = [
    ...(availability?.available_teams || []),
    ...(availability?.unavailable_teams || []),
  ];
  const selectedMemberIds = new Set(
    allTeams
      .filter((team) => (form.team_ids || []).includes(team.id))
      .flatMap((team) => team.members.map((member) => member.id))
  );
  (form.officer_ids || []).forEach((id) => selectedMemberIds.add(id));
  return {
    assigned: selectedMemberIds.size,
    required: Number(form.required_officers) || 0,
    missing: Math.max(0, (Number(form.required_officers) || 0) - selectedMemberIds.size),
    selectedMemberIds,
  };
};

export const additionalOfficerChoices = (availability, selectedTeamIds = []) => {
  const selectedTeamMemberIds = new Set(
    (availability?.available_teams || [])
      .filter((team) => selectedTeamIds.includes(team.id))
      .flatMap((team) => team.members.map((member) => member.id))
  );
  return (availability?.available_officers || []).filter(
    (officer) => !selectedTeamMemberIds.has(officer.id)
  );
};

export const recommendedFormAssignment = (form, recommendation) => ({
  ...form,
  team_ids: recommendation?.team_ids || [],
  officer_ids: recommendation?.officer_ids || [],
});

const KPICard = ({ title, value, subtitle, trend, icon, color }) => {
  const { colors } = useTheme();
  const resolvedColor = color || colors.rosePink;
  return (
    <div className="pp-kpi-card">
    <Card highlight>
      <div className="pp-kpi-card-content" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'var(--pp-kpi-align)', gap: spacing.sm }}>
        <div>
          <p style={{ ...typography.bodySm, color: colors.slate500, margin: 0, marginBottom: spacing.sm }}>{title}</p>
          <h2 className="pp-kpi-value" style={{ ...typography.headingLg, fontSize: 'var(--pp-kpi-font-size)', lineHeight: 'var(--pp-kpi-line-height)', margin: 0, color: colors.slate900 }}>{value}</h2>
          {subtitle && <p style={{ ...typography.bodySm, color: colors.slate500, margin: 0, marginTop: spacing.xs }}>{subtitle}</p>}
          {trend && (
            <div style={{ marginTop: spacing.sm }}>
              <Badge variant={trend.positive ? 'success' : 'warning'}>
                {trend.positive ? '↑' : '↓'} {trend.percent}% vs last week
              </Badge>
            </div>
          )}
        </div>
        {icon && (
          <div className="pp-kpi-icon" style={{
            width: 'var(--pp-kpi-icon-size)', height: 'var(--pp-kpi-icon-size)', background: `${resolvedColor}20`, borderRadius: radius.lg,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 'var(--pp-kpi-icon-font-size)',
          }}>
            <Icon name={icon} size={28} />
          </div>
        )}
      </div>
    </Card>
    </div>
  );
};

// Legacy Table for small inline uses (dashboard fixed rows)
const Table = ({ columns, rows, actions }) => {
  const { colors } = useTheme();
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: typography.bodyMd.fontSize }}>
        <thead>
          <tr style={{ borderBottom: `2px solid ${colors.border}`, background: colors.lightGrey }}>
            {columns.map((col, i) => (
              <th key={i} style={{ padding: spacing.md, textAlign: 'left', ...typography.labelMd, color: colors.slate700, fontWeight: 600 }}>{col}</th>
            ))}
            {actions && <th style={{ ...typography.labelMd, padding: spacing.md }}>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: `1px solid ${colors.border}`, transition: transitions.fast }}
              onMouseEnter={(e) => e.currentTarget.style.background = colors.softPink}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              {Object.values(row.cells || {}).map((cell, j) => (
                <td key={j} style={{ padding: spacing.md, ...typography.bodyMd, color: colors.slate700 }}>{cell}</td>
              ))}
              {actions && <td style={{ padding: spacing.md }}><div style={{ display: 'flex', gap: spacing.sm }}>{actions(row)}</div></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// EnterpriseTable — sortable columns, client-side search filter, pagination
const EnterpriseTable = ({ columns, rows, actions, pageSize = 10 }) => {
  const { colors } = useTheme();
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(1);

  const handleSort = (key) => {
    if (sortKey === key) { setSortDir((d) => d === 'asc' ? 'desc' : 'asc'); }
    else { setSortKey(key); setSortDir('asc'); }
    setPage(1);
  };

  const filtered = useMemo(() => {
    const q = filter.toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      Object.values(row.cells || {}).some((cell) => String(cell).toLowerCase().includes(q))
    );
  }, [rows, filter]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    return [...filtered].sort((a, b) => {
      const av = String(a.cells?.[sortKey] ?? '').toLowerCase();
      const bv = String(b.cells?.[sortKey] ?? '').toLowerCase();
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const paginated = sorted.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="pp-table-component">
      <div className="pp-table-controls" style={{ display: 'flex', gap: spacing.md, marginBottom: spacing.md, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type='text'
          placeholder='Filter rows...'
          value={filter}
          onChange={(e) => { setFilter(e.target.value); setPage(1); }}
          className="pp-table-filter"
          style={{
            padding: `${spacing.sm} ${spacing.md}`, border: `1px solid ${colors.border}`, borderRadius: radius.md,
            ...typography.bodyMd, flex: 1, minWidth: 200, maxWidth: 'var(--pp-table-filter-max-width)', background: colors.cardBg, color: colors.slate900,
          }}
        />
        <span style={{ ...typography.bodySm, color: colors.slate500 }}>
          {sorted.length} row{sorted.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="pp-table-scroller" role="region" aria-label="Scrollable data table" tabIndex="0" style={{ overflowX: 'auto' }}>
        <table className="pp-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: typography.bodyMd.fontSize }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${colors.border}`, background: colors.lightGrey }}>
              {columns.map(({ key, label, sortable = true }) => (
                <th
                  key={key}
                  onClick={() => sortable && handleSort(key)}
                  style={{
                    padding: 'var(--pp-table-cell-padding)', textAlign: 'left', ...typography.labelMd, color: colors.slate700, fontWeight: 600,
                    cursor: sortable ? 'pointer' : 'default', userSelect: 'none',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {label}
                  {sortable && sortKey === key && (sortDir === 'asc' ? ' ↑' : ' ↓')}
                </th>
              ))}
              {actions && <th style={{ ...typography.labelMd, padding: spacing.md, color: colors.slate700 }}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 && (
              <tr><td colSpan={columns.length + (actions ? 1 : 0)} style={{ padding: 'var(--pp-table-cell-padding)', textAlign: 'center', color: colors.slate500 }}>No results</td></tr>
            )}
            {paginated.map((row, i) => (
              <tr key={i}
                style={{ borderBottom: `1px solid ${colors.border}`, transition: transitions.fast }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.softPink}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                {columns.map(({ key }) => (
                  <td key={key} style={{ padding: 'var(--pp-table-cell-padding)', ...typography.bodyMd, color: colors.slate700 }}>
                    {row.cells?.[key] ?? ''}
                  </td>
                ))}
                {actions && <td style={{ padding: 'var(--pp-table-cell-padding)' }}><div className="pp-row-actions" style={{ display: 'flex', gap: spacing.sm }}>{actions(row)}</div></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm, justifyContent: 'flex-end', marginTop: spacing.md }}>
          <Button size='sm' variant='secondary' disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Prev</Button>
          <span style={{ ...typography.bodySm, color: colors.slate500 }}>Page {page} of {totalPages}</span>
          <Button size='sm' variant='secondary' disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next →</Button>
        </div>
      )}
    </div>
  );
};

const Modal = ({ open, onClose, title, children }) => {
  const { colors } = useTheme();
  if (!open) return null;
  const handleBackdropClick = (e) => { if (e.target === e.currentTarget) onClose(); };
  return (
    <div className="pp-modal-backdrop" style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.65)', display: 'flex', alignItems: 'var(--pp-modal-align)', justifyContent: 'center', zIndex: 1050 }}
      onClick={handleBackdropClick} onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div className="pp-modal" role="dialog" aria-modal="true" aria-label={title} style={{ background: colors.cardBg, borderRadius: 'var(--pp-modal-radius)', padding: 'var(--pp-modal-padding)', maxWidth: 'var(--pp-modal-max-width)', width: 'var(--pp-modal-width)', boxShadow: shadows.xl, maxHeight: 'var(--pp-modal-max-height)', overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg }}>
          <h2 style={{ ...typography.headingMd, margin: 0, color: colors.slate900 }}>{title}</h2>
          <button className="pp-icon-button" aria-label={`Close ${title}`} onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: colors.slate500 }}>
            <Icon name='x' size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

const Notification = ({ message, type = 'success', onClose }) => {
  const { colors } = useTheme();
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const variants = {
    success: { bg: '#DCFCE7', text: '#166534', icon: 'checkCircle' },
    error: { bg: '#FEE2E2', text: '#991B1B', icon: 'alertTriangle' },
    info: { bg: '#DBEAFE', text: '#1E40AF', icon: 'info' },
  };

  const v = variants[type];

  return (
    <div className="pp-notification" style={{
      position: 'fixed',
      bottom: 'var(--pp-notification-bottom)',
      right: 'var(--pp-notification-right)',
      background: v.bg,
      color: v.text,
      padding: spacing.md,
      borderRadius: radius.md,
      display: 'flex',
      alignItems: 'center',
      gap: spacing.md,
      boxShadow: shadows.lg,
      zIndex: 1050,
      animation: 'slideIn 0.3s ease-out',
    }}>
      <Icon name={v.icon} size={20} />
      <span style={{ ...typography.bodyMd, fontWeight: 500 }}>{message}</span>
    </div>
  );
};

const ActivityFeed = ({ items }) => {
  const { colors } = useTheme();
  return (
    <div>
      {items.map((item, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            gap: spacing.md,
            paddingBottom: spacing.md,
            marginBottom: spacing.md,
            borderBottom: i < items.length - 1 ? `1px solid ${colors.border}` : 'none',
          }}
        >
          <div style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            background: `${colors.rosePink}20`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <Icon name={item.icon} size={18} color={colors.rosePink} />
          </div>
          <div style={{ flex: 1 }}>
            <p style={{ ...typography.bodyMd, margin: 0, color: colors.slate900, fontWeight: 500 }}>
              {item.title}
            </p>
            <p style={{ ...typography.bodySm, margin: 0, marginTop: spacing.xs, color: colors.slate500 }}>
              {item.description}
            </p>
            <p style={{ ...typography.labelSm, margin: 0, marginTop: spacing.xs, color: colors.slate500 }}>
              {item.time}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};

const formatDashboardTime = (value) => {
  if (!value) return 'Not scheduled';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not scheduled' : date.toLocaleString();
};

const formatActivityAction = (action) => (
  action === 'checkpoint.verify'
    ? CHECKPOINT_CONFIRMATION_COPY.accepted
    : action
    .split('.')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
);

export const DashboardContent = ({ stats, isLoading, error }) => {
  const { colors } = useTheme();

  if (isLoading) {
    return (
      <div>
        <div style={{ marginBottom: spacing.lg }}>
          <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>Dashboard</h1>
          <p role="status" style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>Loading dashboard statistics...</p>
        </div>
        <div className="pp-stats-grid" style={{ marginBottom: spacing.lg }}>
          {[0, 1, 2, 3].map((item) => <SkeletonCard key={item} />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>Dashboard</h1>
        <Card>
          <p role="alert" style={{ ...typography.bodyMd, margin: 0, color: colors.error }}>
            Dashboard statistics are unavailable. Please try again.
          </p>
        </Card>
      </div>
    );
  }

  const activePatrols = stats?.active_patrol_details || [];
  const recentActivity = stats?.recent_activity || [];
  const todaysSchedule = stats?.todays_schedule || [];
  const scheduleStatus = (patrol) => {
    const now = Date.now();
    const startsAt = patrol.start_time ? new Date(patrol.start_time).getTime() : Number.POSITIVE_INFINITY;
    const endsAt = patrol.end_time ? new Date(patrol.end_time).getTime() : Number.POSITIVE_INFINITY;
    if (endsAt < now) return 'Completed';
    if (startsAt <= now) return 'In Progress';
    return 'Scheduled';
  };

  return (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>Dashboard</h1>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Welcome back! Here's what's happening with your security operations today.
        </p>
      </div>

      <div className="pp-stats-grid" style={{ marginBottom: spacing.lg }}>
        <KPICard title="Active Patrols" value={String(stats?.active_patrols ?? 0)} subtitle="Live patrol routes" icon="patrols" />
        <KPICard title="Officers" value={String(stats?.officers ?? 0)} subtitle="Active officer accounts" icon="officers" />
        <KPICard title="Open Incidents" value={String(stats?.open_incidents ?? 0)} subtitle="Needs attention" icon="incidents" />
        <KPICard title="Pending Checkpoints" value={String(stats?.pending_checkpoints ?? 0)} subtitle="Awaiting code confirmation" icon="checkpoints" />
      </div>

      <div className="pp-dashboard-panels" style={{ marginBottom: spacing.lg }}>
        <Card header="Active Patrols">
          <EnterpriseTable
            columns={[
              { key: 'patrol', label: 'Patrol' },
              { key: 'officer', label: 'Officer' },
              { key: 'started', label: 'Started' },
              { key: 'ends', label: 'Ends' },
            ]}
            rows={activePatrols.map((patrol) => ({
              cells: {
                patrol: patrol.name,
                officer: patrol.assigned_to || 'Unassigned',
                started: formatDashboardTime(patrol.start_time),
                ends: patrol.end_time ? formatDashboardTime(patrol.end_time) : 'Open-ended',
              },
            }))}
            pageSize={5}
          />
        </Card>
        <Card header="Recent Activity">
          {recentActivity.length > 0 ? (
            <ActivityFeed items={recentActivity.map((item) => ({
              icon: 'checkCircle',
              title: formatActivityAction(item.action),
              description: item.entity_type,
              time: formatDashboardTime(item.created_at),
            }))} />
          ) : (
            <p style={{ ...typography.bodyMd, margin: 0, color: colors.slate500 }}>No recent activity.</p>
          )}
        </Card>
      </div>

      <Card header="Today's Schedule">
        <EnterpriseTable
          columns={[
            { key: 'time', label: 'Time' },
            { key: 'patrol', label: 'Patrol' },
            { key: 'officer', label: 'Officer' },
            { key: 'status', label: 'Status' },
          ]}
          rows={todaysSchedule.map((patrol) => ({
            cells: {
              time: formatDashboardTime(patrol.start_time),
              patrol: patrol.name,
              officer: patrol.assigned_to || 'Unassigned',
              status: scheduleStatus(patrol),
            },
          }))}
          pageSize={10}
        />
      </Card>
    </div>
  );
};

export const MobileNavigation = ({
  open,
  items,
  activeNav,
  onSelect,
  onClose,
  onLogout,
}) => {
  const { colors } = useTheme();
  const drawerRef = useRef(null);
  const closeButtonRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButtonRef.current?.focus();

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !drawerRef.current) return;
      const focusable = drawerRef.current.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="pp-mobile-nav">
      <button className="pp-drawer-backdrop" aria-label="Close navigation" onClick={onClose} />
      <aside
        ref={drawerRef}
        id="mobile-navigation"
        className="pp-mobile-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Main navigation"
        style={{ background: colors.sidebarBg, color: colors.sidebarText }}
      >
        <div className="pp-drawer-header">
          <h2 style={{ ...typography.headingSm, margin: 0, color: colors.sidebarText }}>PatrolPro</h2>
          <button
            ref={closeButtonRef}
            className="pp-icon-button"
            aria-label="Close navigation"
            onClick={onClose}
            style={{ background: 'transparent', border: 0, color: colors.sidebarText }}
          >
            <Icon name="x" color={colors.sidebarText} />
          </button>
        </div>
        <nav className="pp-drawer-nav" aria-label="Mobile">
          {items.map((item) => (
            <button
              key={item.id}
              className="pp-drawer-nav-item"
              aria-current={activeNav === item.id ? 'page' : undefined}
              onClick={() => {
                onSelect(item.id);
                onClose();
              }}
              style={{
                marginBottom: spacing.xs,
                background: activeNav === item.id ? colors.rosePink : 'transparent',
                color: colors.sidebarText,
              }}
            >
              <Icon name={item.icon} size={20} color={colors.sidebarText} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <button
          className="pp-drawer-logout"
          onClick={() => {
            onClose();
            onLogout();
          }}
          style={{
            marginTop: spacing.md,
            background: 'transparent',
            color: colors.sidebarText,
            borderTop: `1px solid ${colors.slate700}`,
          }}
        >
          <Icon name="logout" size={20} color={colors.sidebarText} />
          <span>Logout</span>
        </button>
      </aside>
    </div>
  );
};

// ==================== AUTH CONTENT COMPONENT ====================

const AuthContent = ({ 
  authTab, setAuthTab, 
  email, setEmail, 
  password, setPassword, 
  fullName, setFullName, 
  companyName, setCompanyName,
  handleLogin, handleRegister 
}) => {
  const { colors } = useTheme();
  return (
  <div className="pp-auth" style={{ maxWidth: 500, margin: '0 auto', paddingTop: 'var(--pp-auth-padding-top)' }}>
    <Card>
      <h1 style={{ ...typography.headingLg, margin: 0, marginBottom: spacing.lg, textAlign: 'center', color: colors.slate900 }}>
        Security Operations Platform
      </h1>
      <p style={{ ...typography.bodyMd, margin: 0, marginBottom: spacing.lg, textAlign: 'center', color: colors.slate500 }}>
        Manage patrols, incidents, and security operations
      </p>

      <div style={{ display: 'flex', gap: spacing.md, marginBottom: spacing.lg }}>
        <button onClick={() => setAuthTab('login')} style={{
          flex: 1, padding: spacing.md,
          background: authTab === 'login' ? colors.rosePink : 'transparent',
          color: authTab === 'login' ? '#fff' : colors.slate700,
          border: `2px solid ${authTab === 'login' ? colors.rosePink : colors.border}`,
          borderRadius: radius.md, cursor: 'pointer', fontWeight: 600, transition: transitions.fast,
        }}>Login</button>
        <button onClick={() => setAuthTab('register')} style={{
          flex: 1, padding: spacing.md,
          background: authTab === 'register' ? colors.rosePink : 'transparent',
          color: authTab === 'register' ? '#fff' : colors.slate700,
          border: `2px solid ${authTab === 'register' ? colors.rosePink : colors.border}`,
          borderRadius: radius.md, cursor: 'pointer', fontWeight: 600, transition: transitions.fast,
        }}>Register</button>
      </div>

      {authTab === 'login' ? (
        <>
          <TextField label="Email" value={email} onChange={setEmail} placeholder="owner@security.com" autoFocus={true} />
          <TextField label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" />
          <Button onClick={handleLogin} fullWidth>Sign In</Button>
        </>
      ) : (
        <>
          <TextField label="Company Name" value={companyName} onChange={setCompanyName} placeholder="Acme Security Ltd" autoFocus={true} />
          <TextField label="Owner Name" value={fullName} onChange={setFullName} placeholder="John Doe" />
          <TextField label="Email" value={email} onChange={setEmail} placeholder="john@security.com" />
          <TextField label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" />
          <Button onClick={handleRegister} fullWidth>Create Account</Button>
        </>
      )}
    </Card>
  </div>
  );
};

// ==================== PATROLS CONTENT COMPONENT ====================

const PatrolsContent = ({
  patrols,
  patrolForm,
  setPatrolForm,
  showPatrolModal,
  setShowPatrolModal,
  showEditPatrolModal,
  startEditPatrol,
  handleDeletePatrol,
  onCloseEditPatrol,
  handleCreatePatrol,
  handleUpdatePatrol,
  loadPatrols,
  availability,
  availabilityLoading,
}) => {
  const { colors } = useTheme();
  const coverage = staffingCoverage(patrolForm, availability);
  const additionalOfficers = additionalOfficerChoices(
    availability, patrolForm.team_ids,
  );
  const selectedTeamMemberCount = (
    availability?.available_teams || []
  ).filter((team) => patrolForm.team_ids.includes(team.id))
    .flatMap((team) => team.members).length;
  const canSubmit = (
    Boolean(patrolForm.name)
    && Boolean(patrolForm.start_time)
    && Boolean(patrolForm.end_time)
    && new Date(patrolForm.end_time) > new Date(patrolForm.start_time)
    && coverage.missing === 0
    && !availabilityLoading
  );
  const selectTeams = (team_ids) => {
    const validOfficerIds = additionalOfficerChoices(availability, team_ids)
      .map((officer) => officer.id);
    setPatrolForm({
      ...patrolForm,
      team_ids,
      officer_ids: patrolForm.officer_ids.filter((id) => validOfficerIds.includes(id)),
    });
  };
  const openNewPatrol = () => {
    const schedule = getDefaultPatrolSchedule();
    setPatrolForm({
      name: '',
      description: '',
      assigned_to: '',
      required_officers: 1,
      officer_ids: [],
      team_ids: [],
      ...schedule,
    });
    setShowPatrolModal(true);
  };
  return (
  <div>
    <div className="pp-page-heading-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg }}>
      <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Patrols</h1>
      <div className="pp-page-actions" style={{ display: 'flex', gap: spacing.md }}>
        <Button onClick={loadPatrols} variant="secondary" icon="load">Refresh</Button>
        <Button onClick={openNewPatrol} icon="add">New Patrol</Button>
      </div>
    </div>

    <Modal
      open={showPatrolModal}
      onClose={() => setShowPatrolModal(false)}
      title="Create New Patrol"
    >
      <TextField
        label="Patrol Name"
        value={patrolForm.name}
        onChange={(v) => setPatrolForm({ ...patrolForm, name: v })}
        placeholder="e.g., Night Shift - Zone A"
        autoFocus={true}
      />
      <TextField
        label="Description"
        value={patrolForm.description}
        onChange={(v) => setPatrolForm({ ...patrolForm, description: v })}
        placeholder="Patrol details and objectives"
      />
      <TextField
        label="Start Time"
        type="datetime-local"
        value={patrolForm.start_time}
        onChange={(v) => setPatrolForm({ ...patrolForm, start_time: v })}
      />
      <TextField
        label="End Time"
        type="datetime-local"
        value={patrolForm.end_time}
        onChange={(v) => setPatrolForm({ ...patrolForm, end_time: v })}
      />
      <TextField
        label="Officers Required"
        type="number"
        value={patrolForm.required_officers}
        onChange={(v) => setPatrolForm({ ...patrolForm, required_officers: Number(v) })}
      />
      {availabilityLoading ? (
        <p>Checking live availability…</p>
      ) : (
        <>
          {availability?.recommendation && (
            <Card highlight>
              <p style={{ ...typography.labelMd, marginBottom: spacing.xs }}>Recommended Assignment</p>
              <p style={{ ...typography.bodySm, color: colors.slate500, marginBottom: spacing.sm }}>
                {availability.recommendation.explanation}
              </p>
              <Button
                size="sm"
                onClick={() => setPatrolForm(recommendedFormAssignment(
                  patrolForm, availability.recommendation,
                ))}
              >
                Use Recommended Assignment
              </Button>
            </Card>
          )}
          <SearchableMultiSelect
            label="Assign Available Teams (preferred)"
            options={(availability?.available_teams || []).map((team) => ({
              value: team.id,
              label: `${team.name} · ${team.members.length} officers · Available · ${team.workload_count} upcoming`,
            }))}
            selected={patrolForm.team_ids}
            onChange={selectTeams}
            emptyMessage="Choose valid start and end times to see available teams"
          />
          <SearchableMultiSelect
            label="Assign Available Officers"
            options={additionalOfficers.map((officer) => ({
              value: officer.id,
              label: `${officer.full_name || 'Unnamed officer'} · ${officer.staff_identifier} · ${officer.team_name || 'No team'} · Available · ${officer.workload_count} upcoming`,
            }))}
            selected={patrolForm.officer_ids}
            onChange={(officer_ids) => setPatrolForm({ ...patrolForm, officer_ids })}
            emptyMessage="Choose valid start and end times to see available officers"
          />
          {(availability?.unavailable_officers || []).length > 0 && (
            <p style={{ ...typography.bodySm, color: colors.slate500 }}>
              Unavailable: {availability.unavailable_officers.map((officer) => (
                `${officer.full_name || officer.staff_identifier} — ${officer.reason}`
              )).join('; ')}
            </p>
          )}
          {selectedTeamMemberCount > 0 && (
            <p style={{ ...typography.bodySm, color: colors.slate500 }}>
              {selectedTeamMemberCount} team member(s) are already included and removed from additional choices.
            </p>
          )}
        </>
      )}
      <div role="status" aria-live="polite" style={{
        padding: spacing.md,
        marginTop: spacing.sm,
        borderRadius: radius.md,
        background: coverage.missing === 0 ? '#DCFCE7' : '#FEF3C7',
        color: coverage.missing === 0 ? '#166534' : '#92400E',
      }}>
        <strong>{coverage.assigned} of {coverage.required} officers assigned.</strong>
        {coverage.missing > 0 && ` Add ${coverage.missing} more officer(s) to continue.`}
      </div>
      <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
        <Button onClick={() => setShowPatrolModal(false)} variant="secondary" fullWidth>Cancel</Button>
        <Button onClick={handleCreatePatrol} fullWidth disabled={!canSubmit}>Create Patrol</Button>
      </div>
    </Modal>

    <div className="pp-card-grid">
      {patrols.map((patrol) => (
        <Card key={patrol.id} highlight>
          <h3 style={{ ...typography.headingSm, margin: 0, marginBottom: spacing.sm, color: colors.slate900 }}>
            {patrol.name}
          </h3>
          <p style={{ ...typography.bodySm, margin: 0, color: colors.slate500, marginBottom: spacing.md }}>
            {patrol.description}
          </p>
          <div style={{ marginBottom: spacing.md }}>
            <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Assigned To</p>
            <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 600, color: colors.slate900 }}>
              {(patrol.assignment_names || []).join(', ') || patrol.assigned_to || 'Unassigned'}
            </p>
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: spacing.md,
            marginBottom: spacing.md,
            paddingBottom: spacing.md,
            borderBottom: `1px solid ${colors.border}`,
          }}>
            <div>
              <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Start</p>
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 500 }}>
                {new Date(patrol.start_time).toLocaleString()}
              </p>
            </div>
            <div>
              <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>End</p>
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 500 }}>
                {new Date(patrol.end_time).toLocaleString()}
              </p>
            </div>
          </div>
          <div className="pp-row-actions" style={{ display: 'flex', gap: spacing.sm }}>
            <Button variant="secondary" size="sm" fullWidth icon="edit" onClick={() => startEditPatrol(patrol)}>Edit</Button>
            <Button variant="danger" size="sm" fullWidth icon="trash" onClick={() => handleDeletePatrol(patrol.id)}>Delete</Button>
          </div>
        </Card>
      ))}
    </div>

    {patrols.length === 0 && (
      <Card>
        <div style={{
          textAlign: 'center',
          padding: spacing.xl,
        }}>
          <p style={{ ...typography.headingSm, color: colors.slate500, marginBottom: spacing.md }}>
            No patrols yet
          </p>
          <p style={{ ...typography.bodyMd, color: colors.slate500, marginBottom: spacing.lg }}>
            Create your first patrol to get started with security operations
          </p>
          <Button onClick={openNewPatrol} icon="add">Create First Patrol</Button>
        </div>
      </Card>
    )}

    <Modal open={showEditPatrolModal} onClose={onCloseEditPatrol} title="Edit Patrol">
        <TextField
          label="Patrol Name"
          value={patrolForm.name}
          onChange={(v) => setPatrolForm({ ...patrolForm, name: v })}
          placeholder="e.g., Night Shift - Zone A"
          autoFocus={true}
        />
        <TextField
          label="Description"
          value={patrolForm.description}
          onChange={(v) => setPatrolForm({ ...patrolForm, description: v })}
          placeholder="Patrol details and objectives"
        />
        <TextField
          label="Start Time"
          type="datetime-local"
          value={patrolForm.start_time}
          onChange={(v) => setPatrolForm({ ...patrolForm, start_time: v })}
        />
        <TextField
          label="End Time"
          type="datetime-local"
          value={patrolForm.end_time}
          onChange={(v) => setPatrolForm({ ...patrolForm, end_time: v })}
        />
        <TextField
          label="Officers Required"
          type="number"
          value={patrolForm.required_officers}
          onChange={(v) => setPatrolForm({ ...patrolForm, required_officers: Number(v) })}
        />
        {availabilityLoading ? <p>Checking live availability…</p> : (
          <>
            {availability?.recommendation && (
              <Card highlight>
                <p style={{ ...typography.labelMd }}>Recommended Assignment</p>
                <p style={{ ...typography.bodySm, color: colors.slate500 }}>
                  {availability.recommendation.explanation}
                </p>
                <Button size="sm" onClick={() => setPatrolForm(recommendedFormAssignment(
                  patrolForm, availability.recommendation,
                ))}>Use Recommended Assignment</Button>
              </Card>
            )}
            <SearchableMultiSelect
              label="Assign Available Teams (preferred)"
              options={(availability?.available_teams || []).map((team) => ({
                value: team.id,
                label: `${team.name} · ${team.members.length} officers · Available · ${team.workload_count} upcoming`,
              }))}
              selected={patrolForm.team_ids}
              onChange={selectTeams}
            />
            <SearchableMultiSelect
              label="Assign Available Officers"
              options={additionalOfficers.map((officer) => ({
                value: officer.id,
                label: `${officer.full_name || 'Unnamed officer'} · ${officer.staff_identifier} · ${officer.team_name || 'No team'} · Available · ${officer.workload_count} upcoming`,
              }))}
              selected={patrolForm.officer_ids}
              onChange={(officer_ids) => setPatrolForm({ ...patrolForm, officer_ids })}
            />
          </>
        )}
        <div role="status" aria-live="polite" style={{
          padding: spacing.md,
          borderRadius: radius.md,
          background: coverage.missing === 0 ? '#DCFCE7' : '#FEF3C7',
          color: coverage.missing === 0 ? '#166534' : '#92400E',
        }}>
          <strong>{coverage.assigned} of {coverage.required} officers assigned.</strong>
          {coverage.missing > 0 && ` Add ${coverage.missing} more officer(s) to continue.`}
        </div>
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button onClick={onCloseEditPatrol} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={handleUpdatePatrol} fullWidth disabled={!canSubmit}>Update Patrol</Button>
        </div>
    </Modal>
  </div>
  );
};

// ==================== MAIN APP COMPONENT ====================

function AppInner() {
  const { colors, dark, toggle } = useTheme();
  const [activeNav, setActiveNav] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [token, setToken] = useState('');
  const [authContext, setAuthContext] = useState(null);
  const [notification, setNotification] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState('');
  const mobileMenuButtonRef = useRef(null);

  // Auth state
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [password, setPassword] = useState('');
  const [authTab, setAuthTab] = useState('login');

  // Patrols
  const [patrols, setPatrols] = useState([]);
  const emptyPatrolForm = {
    name: '',
    description: '',
    assigned_to: '',
    start_time: '',
    end_time: '',
    required_officers: 1,
    officer_ids: [],
    team_ids: [],
  };
  const [patrolForm, setPatrolForm] = useState(emptyPatrolForm);
  const [showPatrolModal, setShowPatrolModal] = useState(false);
  const [showEditPatrolModal, setShowEditPatrolModal] = useState(false);
  const [editingPatrolId, setEditingPatrolId] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);

  // Officers
  const [officers, setOfficers] = useState([]);
  const [officersLoading, setOfficersLoading] = useState(false);
  const [officersError, setOfficersError] = useState('');
  const [teams, setTeams] = useState([]);
  const [myTeam, setMyTeam] = useState(null);
  const [teamsLoading, setTeamsLoading] = useState(false);
  const [teamForm, setTeamForm] = useState({
    name: '',
    leader_user_id: '',
    notes: '',
    status: 'active',
    member_user_ids: [],
  });
  const [showTeamModal, setShowTeamModal] = useState(false);
  const [editingTeamId, setEditingTeamId] = useState(null);

  // Incidents
  const [incidents, setIncidents] = useState([]);
  const emptyIncidentForm = {
    title: '', description: '', category: 'security', location: '', severity: 'medium',
    status: 'open', resolution_notes: '', patrol_id: '', customer_id: '', reported_at: '',
  };
  const [incidentForm, setIncidentForm] = useState(emptyIncidentForm);
  const [showIncidentModal, setShowIncidentModal] = useState(false);
  const [showEditIncidentModal, setShowEditIncidentModal] = useState(false);
  const [editingIncidentId, setEditingIncidentId] = useState(null);
  const [showRemoveIncidentModal, setShowRemoveIncidentModal] = useState(false);
  const [removingIncidentId, setRemovingIncidentId] = useState(null);

  // Checkpoints
  const [checkpoints, setCheckpoints] = useState([]);
  const emptyCheckpointForm = {
    name: '', code: '', patrol_id: '', location_label: '', status: 'pending', nfc_tag: '',
  };
  const [checkpointForm, setCheckpointForm] = useState(emptyCheckpointForm);
  const [showCheckpointModal, setShowCheckpointModal] = useState(false);
  const [showEditCheckpointModal, setShowEditCheckpointModal] = useState(false);
  const [editingCheckpointId, setEditingCheckpointId] = useState(null);
  const [showRemoveCheckpointModal, setShowRemoveCheckpointModal] = useState(false);
  const [removingCheckpointId, setRemovingCheckpointId] = useState(null);
  const [verifyingCheckpoint, setVerifyingCheckpoint] = useState(null);
  const [verificationCode, setVerificationCode] = useState('');

  // Users
  const [users, setUsers] = useState([]);

  // Vehicles (backed by devices API)
  const [vehicles, setVehicles] = useState([]);
  const [vehicleForm, setVehicleForm] = useState({ name: '', serial_number: '', status: 'active' });
  const [showVehicleModal, setShowVehicleModal] = useState(false);
  const [showEditVehicleModal, setShowEditVehicleModal] = useState(false);
  const [editingVehicleId, setEditingVehicleId] = useState(null);
  const [showRemoveVehicleModal, setShowRemoveVehicleModal] = useState(false);
  const [removingVehicleId, setRemovingVehicleId] = useState(null);

  // Customers
  const [customers, setCustomers] = useState([]);
  const [customerForm, setCustomerForm] = useState({ name: '', contact_email: '', phone: '', address: '' });
  const [showCustomerModal, setShowCustomerModal] = useState(false);
  const [showEditCustomerModal, setShowEditCustomerModal] = useState(false);
  const [editingCustomerId, setEditingCustomerId] = useState(null);
  const [showArchiveCustomerModal, setShowArchiveCustomerModal] = useState(false);
  const [archivingCustomerId, setArchivingCustomerId] = useState(null);

  const notify = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const headers = token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };

  const apiCall = async (url, opts) => {
    try {
      const finalHeaders = { ...headers, ...opts.headers };
      const response = await fetch(url, { ...opts, headers: finalHeaders });
      const responseText = await response.text();
      const data = responseText ? JSON.parse(responseText) : null;
      if (!response.ok) {
        if (response.status === 401 && token) {
          setToken('');
          setAuthContext(null);
          setMobileNavOpen(false);
        }
        let message = 'API Error';
        if (typeof data?.detail === 'string') {
          message = data.detail;
        } else if (Array.isArray(data?.detail) && data.detail.length > 0) {
          const first = data.detail[0];
          message = first?.msg || JSON.stringify(first);
        } else if (data?.detail) {
          message = JSON.stringify(data.detail);
        }
        throw new Error(message);
      }
      return { ok: true, data };
    } catch (error) {
      notify(error.message, 'error');
      return { ok: false, data: null };
    }
  };

  const loadDashboardStats = async () => {
    setDashboardLoading(true);
    setDashboardError('');
    const result = await apiCall(`${API_BASE}/dashboard/stats`, { method: 'GET' });
    if (result.ok) {
      setDashboardStats(result.data);
    } else {
      setDashboardStats(null);
      setDashboardError('Dashboard statistics are unavailable.');
    }
    setDashboardLoading(false);
  };

  const handleRegister = async () => {
    if (!email || !password || !fullName || !companyName) {
      notify('Please fill all fields', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_name: companyName,
        business_email: email,
        owner_name: fullName,
        owner_email: email,
        password,
      }),
    });
    if (result.ok) {
      notify('Registration successful! Please login.');
      setAuthTab('login');
      setEmail('');
      setPassword('');
      setFullName('');
      setCompanyName('');
    }
  };

  const handleLogin = async () => {
    if (!email || !password) {
      notify('Please enter email and password', 'error');
      return;
    }
    const form = new URLSearchParams({ username: email, password });
    const result = await apiCall(`${API_BASE}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    });
    if (result.ok) {
      const accessToken = result.data.access_token;
      const contextResult = await apiCall(`${API_BASE}/auth/me`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${accessToken}` },
      });
      if (!contextResult.ok) return;
      setAuthContext(contextResult.data);
      setToken(accessToken);
      notify('Logged in successfully!');
      setEmail('');
      setPassword('');
    }
  };

  const handleCreatePatrol = async () => {
    if (!patrolForm.name || !patrolForm.start_time || !patrolForm.end_time) {
      notify('Name, start time and end time are required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/patrols/`, {
      method: 'POST',
      body: JSON.stringify(patrolForm),
    });
    if (result.ok) {
      notify('Patrol created successfully!');
      setPatrols([...patrols, result.data]);
      loadDashboardStats();
      setPatrolForm(emptyPatrolForm);
      setShowPatrolModal(false);
    }
  };

  const loadPatrols = async () => {
    const result = await apiCall(`${API_BASE}/patrols/`, { method: 'GET' });
    if (result.ok) {
      setPatrols(result.data);
      notify('Patrols loaded');
    }
  };

  const handleUpdatePatrol = async () => {
    if (!patrolForm.name || !patrolForm.start_time || !patrolForm.end_time) {
      notify('Name, start time and end time are required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/patrols/${editingPatrolId}`, {
      method: 'PUT',
      body: JSON.stringify(patrolForm),
    });
    if (result.ok) {
      notify('Patrol updated successfully!');
      setPatrols(patrols.map((p) => p.id === editingPatrolId ? result.data : p));
      loadDashboardStats();
      setPatrolForm(emptyPatrolForm);
      setShowEditPatrolModal(false);
      setEditingPatrolId(null);
    }
  };

  const handleDeletePatrol = async (patrolId) => {
    if (!window.confirm('Are you sure you want to delete this patrol?')) return;
    const result = await apiCall(`${API_BASE}/patrols/${patrolId}`, { method: 'DELETE' });
    if (result.ok) {
      notify('Patrol deleted successfully!');
      setPatrols(patrols.filter((p) => p.id !== patrolId));
      loadDashboardStats();
    }
  };

  const startEditPatrol = (patrol) => {
    setPatrolForm({
      name: patrol.name,
      description: patrol.description,
      assigned_to: patrol.assigned_to,
      start_time: patrol.start_time,
      end_time: patrol.end_time,
      required_officers: patrol.required_officers || 1,
      officer_ids: patrol.officer_ids || [],
      team_ids: patrol.team_ids || [],
    });
    setEditingPatrolId(patrol.id);
    setShowEditPatrolModal(true);
  };

  const closeEditPatrol = () => {
    setShowEditPatrolModal(false);
    setEditingPatrolId(null);
  };

  const loadOfficers = async () => {
    setOfficersLoading(true);
    setOfficersError('');
    const result = await apiCall(`${API_BASE}/users/officers`, { method: 'GET' });
    if (result.ok) {
      setOfficers(result.data);
    } else {
      setOfficers([]);
      setOfficersError('Officers are unavailable.');
    }
    setOfficersLoading(false);
  };

  const loadTeams = async () => {
    setTeamsLoading(true);
    const result = await apiCall(`${API_BASE}/teams`, { method: 'GET' });
    if (result.ok) setTeams(result.data);
    setTeamsLoading(false);
  };

  const loadMyTeam = async () => {
    const result = await apiCall(`${API_BASE}/teams/mine`, { method: 'GET' });
    if (result.ok) setMyTeam(result.data);
  };

  const saveTeam = async () => {
    if (!teamForm.name || teamForm.member_user_ids.length === 0) {
      notify('Team name and at least one officer are required', 'error');
      return;
    }
    const method = editingTeamId ? 'PUT' : 'POST';
    const url = editingTeamId ? `${API_BASE}/teams/${editingTeamId}` : `${API_BASE}/teams`;
    const result = await apiCall(url, {
      method,
      body: JSON.stringify({
        ...teamForm,
        leader_user_id: teamForm.leader_user_id ? Number(teamForm.leader_user_id) : null,
      }),
    });
    if (result.ok) {
      await loadTeams();
      setShowTeamModal(false);
      setEditingTeamId(null);
      setTeamForm({
        name: '', leader_user_id: '', notes: '', status: 'active', member_user_ids: [],
      });
      notify(editingTeamId ? 'Team updated' : 'Team created');
    }
  };

  const editTeam = (team) => {
    setTeamForm({
      name: team.name,
      leader_user_id: team.leader_user_id || '',
      notes: team.notes || '',
      status: team.status,
      member_user_ids: team.members.map((member) => member.id),
    });
    setEditingTeamId(team.id);
    setShowTeamModal(true);
  };

  const archiveTeam = async (team) => {
    if (!window.confirm(`Archive ${team.name}? It will no longer be assignable.`)) return;
    const result = await apiCall(`${API_BASE}/teams/${team.id}`, { method: 'DELETE' });
    if (result.ok) {
      await loadTeams();
      notify('Team archived');
    }
  };

  const toDateTimeLocal = (value) => {
    if (!value) return '';
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return '';

    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const startEditIncident = (incident) => {
    setIncidentForm({
      title: incident.title,
      description: incident.description || '',
      category: incident.category || 'security',
      location: incident.location || '',
      severity: incident.severity,
      status: incident.status,
      resolution_notes: incident.resolution_notes || '',
      patrol_id: incident.patrol_id || '',
      customer_id: incident.customer_id || '',
      reported_at: incident.reported_at,
    });
    setEditingIncidentId(incident.id);
    setShowEditIncidentModal(true);
  };

  const closeEditIncident = () => {
    setShowEditIncidentModal(false);
    setEditingIncidentId(null);
    setIncidentForm(emptyIncidentForm);
  };

  const incidentPayload = () => ({
    ...incidentForm,
    patrol_id: incidentForm.patrol_id ? Number(incidentForm.patrol_id) : null,
    customer_id: incidentForm.customer_id ? Number(incidentForm.customer_id) : null,
    device_id: null,
    reported_at: incidentForm.reported_at || new Date().toISOString(),
  });

  const loadIncidents = async () => {
    const result = await apiCall(`${API_BASE}/alerts/`, { method: 'GET' });
    if (result.ok) setIncidents(result.data);
  };

  const handleCreateIncident = async () => {
    if (!incidentForm.title || !incidentForm.location) {
      notify('Title and location are required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/alerts/`, {
      method: 'POST',
      body: JSON.stringify(incidentPayload()),
    });
    if (result.ok) {
      setIncidents([result.data, ...incidents]);
      setShowIncidentModal(false);
      setIncidentForm(emptyIncidentForm);
      loadDashboardStats();
      notify('Incident reported');
    }
  };

  const handleUpdateIncident = async () => {
    const result = await apiCall(`${API_BASE}/alerts/${editingIncidentId}`, {
      method: 'PUT',
      body: JSON.stringify(incidentPayload()),
    });
    if (result.ok) {
      setIncidents(incidents.map((incident) => (
        incident.id === editingIncidentId ? result.data : incident
      )));
      loadDashboardStats();
      notify('Incident updated');
      closeEditIncident();
    }
  };

  const requestRemoveIncident = (incidentId) => {
    setRemovingIncidentId(incidentId);
    setShowRemoveIncidentModal(true);
  };

  const closeRemoveIncident = () => {
    setShowRemoveIncidentModal(false);
    setRemovingIncidentId(null);
  };

  const confirmRemoveIncident = async () => {
    if (removingIncidentId === null) return;
    const result = await apiCall(`${API_BASE}/alerts/${removingIncidentId}`, { method: 'DELETE' });
    if (result.ok) {
      setIncidents(incidents.filter((i) => i.id !== removingIncidentId));
      loadDashboardStats();
      notify('Incident archived');
      closeRemoveIncident();
    }
  };

  const startEditCheckpoint = (checkpoint) => {
    setCheckpointForm({
      name: checkpoint.name,
      code: checkpoint.code,
      patrol_id: checkpoint.patrol_id || '',
      location_label: checkpoint.location_label || '',
      status: checkpoint.status,
      nfc_tag: checkpoint.nfc_tag || '',
    });
    setEditingCheckpointId(checkpoint.id);
    setShowEditCheckpointModal(true);
  };

  const closeEditCheckpoint = () => {
    setShowEditCheckpointModal(false);
    setEditingCheckpointId(null);
    setCheckpointForm(emptyCheckpointForm);
  };

  const checkpointPayload = () => ({
    ...checkpointForm,
    patrol_id: checkpointForm.patrol_id ? Number(checkpointForm.patrol_id) : null,
    latitude: null,
    longitude: null,
  });

  const loadCheckpoints = async () => {
    const result = await apiCall(`${API_BASE}/checkpoints/`, { method: 'GET' });
    if (result.ok) setCheckpoints(result.data);
  };

  const handleCreateCheckpoint = async () => {
    if (!checkpointForm.name || !checkpointForm.code || !checkpointForm.location_label) {
      notify('Name, code and location are required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/checkpoints/`, {
      method: 'POST',
      body: JSON.stringify(checkpointPayload()),
    });
    if (result.ok) {
      setCheckpoints([...checkpoints, result.data]);
      setShowCheckpointModal(false);
      setCheckpointForm(emptyCheckpointForm);
      loadDashboardStats();
      notify('Checkpoint created');
    }
  };

  const handleUpdateCheckpoint = async () => {
    const result = await apiCall(`${API_BASE}/checkpoints/${editingCheckpointId}`, {
      method: 'PUT',
      body: JSON.stringify(checkpointPayload()),
    });
    if (result.ok) {
      setCheckpoints(checkpoints.map((checkpoint) => (
        checkpoint.id === editingCheckpointId ? result.data : checkpoint
      )));
      notify('Checkpoint updated');
      closeEditCheckpoint();
    }
  };

  const requestRemoveCheckpoint = (checkpointId) => {
    setRemovingCheckpointId(checkpointId);
    setShowRemoveCheckpointModal(true);
  };

  const closeRemoveCheckpoint = () => {
    setShowRemoveCheckpointModal(false);
    setRemovingCheckpointId(null);
  };

  const confirmRemoveCheckpoint = async () => {
    if (removingCheckpointId === null) return;
    const result = await apiCall(`${API_BASE}/checkpoints/${removingCheckpointId}`, { method: 'DELETE' });
    if (result.ok) {
      setCheckpoints(checkpoints.filter((c) => c.id !== removingCheckpointId));
      loadDashboardStats();
      notify('Checkpoint archived');
      closeRemoveCheckpoint();
    }
  };

  const verifyCheckpoint = async () => {
    if (!verifyingCheckpoint || !verificationCode) {
      notify('Checkpoint code is required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/checkpoints/${verifyingCheckpoint.id}/verify`, {
      method: 'POST',
      body: JSON.stringify({ code: verificationCode }),
    });
    if (result.ok) {
      setCheckpoints(checkpoints.map((checkpoint) => (
        checkpoint.id === verifyingCheckpoint.id ? result.data : checkpoint
      )));
      setVerifyingCheckpoint(null);
      setVerificationCode('');
      loadDashboardStats();
      notify(CHECKPOINT_CONFIRMATION_COPY.accepted);
    }
  };

  const formatDateTime = (value) => {
    if (!value) return 'Not set';
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return 'Not set';
    return date.toLocaleString();
  };

  const loadVehicles = async () => {
    const result = await apiCall(`${API_BASE}/devices/`, { method: 'GET' });
    if (result.ok) {
      setVehicles(result.data);
    }
  };

  const handleCreateVehicle = async () => {
    if (!vehicleForm.name || !vehicleForm.serial_number) {
      notify('Vehicle name and unit ID are required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/devices/`, {
      method: 'POST',
      body: JSON.stringify(vehicleForm),
    });
    if (result.ok) {
      setVehicles([...vehicles, result.data]);
      setVehicleForm({ name: '', serial_number: '', status: 'active' });
      setShowVehicleModal(false);
      notify('Vehicle added successfully!');
    }
  };

  const startEditVehicle = (vehicle) => {
    setVehicleForm({
      name: vehicle.name,
      serial_number: vehicle.serial_number,
      status: vehicle.status || 'active',
    });
    setEditingVehicleId(vehicle.id);
    setShowEditVehicleModal(true);
  };

  const closeEditVehicle = () => {
    setShowEditVehicleModal(false);
    setEditingVehicleId(null);
    setVehicleForm({ name: '', serial_number: '', status: 'active' });
  };

  const handleUpdateVehicle = async () => {
    if (!vehicleForm.name || !vehicleForm.serial_number) {
      notify('Vehicle name and unit ID are required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/devices/${editingVehicleId}`, {
      method: 'PUT',
      body: JSON.stringify(vehicleForm),
    });
    if (result.ok) {
      setVehicles(vehicles.map((v) => (v.id === editingVehicleId ? result.data : v)));
      notify('Vehicle updated successfully!');
      closeEditVehicle();
    }
  };

  const requestRemoveVehicle = (vehicleId) => {
    setRemovingVehicleId(vehicleId);
    setShowRemoveVehicleModal(true);
  };

  const closeRemoveVehicle = () => {
    setShowRemoveVehicleModal(false);
    setRemovingVehicleId(null);
  };

  const confirmRemoveVehicle = async () => {
    if (removingVehicleId === null) return;
    const result = await apiCall(`${API_BASE}/devices/${removingVehicleId}`, { method: 'DELETE' });
    if (result.ok) {
      setVehicles(vehicles.filter((v) => v.id !== removingVehicleId));
      notify('Vehicle removed successfully!');
      closeRemoveVehicle();
    }
  };

  const loadCustomers = async () => {
    const result = await apiCall(`${API_BASE}/customers/`, { method: 'GET' });
    if (result.ok) {
      setCustomers(result.data);
    }
  };

  const handleCreateCustomer = async () => {
    if (!customerForm.name) {
      notify('Customer name is required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/customers/`, {
      method: 'POST',
      body: JSON.stringify(customerForm),
    });
    if (result.ok) {
      setCustomers([...customers, result.data]);
      setCustomerForm({ name: '', contact_email: '', phone: '', address: '' });
      setShowCustomerModal(false);
      notify('Customer created');
    }
  };

  const startEditCustomer = (customer) => {
    setCustomerForm({
      name: customer.name,
      contact_email: customer.contact_email || '',
      phone: customer.phone || '',
      address: customer.address || '',
    });
    setEditingCustomerId(customer.id);
    setShowEditCustomerModal(true);
  };

  const closeEditCustomer = () => {
    setShowEditCustomerModal(false);
    setEditingCustomerId(null);
    setCustomerForm({ name: '', contact_email: '', phone: '', address: '' });
  };

  const handleUpdateCustomer = async () => {
    if (!customerForm.name) {
      notify('Customer name is required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/customers/${editingCustomerId}`, {
      method: 'PUT',
      body: JSON.stringify(customerForm),
    });
    if (result.ok) {
      setCustomers(customers.map((customer) => (
        customer.id === editingCustomerId ? result.data : customer
      )));
      notify('Customer updated');
      closeEditCustomer();
    }
  };

  const requestArchiveCustomer = (customerId) => {
    setArchivingCustomerId(customerId);
    setShowArchiveCustomerModal(true);
  };

  const closeArchiveCustomer = () => {
    setShowArchiveCustomerModal(false);
    setArchivingCustomerId(null);
  };

  const confirmArchiveCustomer = async () => {
    if (archivingCustomerId === null) return;
    const result = await apiCall(`${API_BASE}/customers/${archivingCustomerId}`, { method: 'DELETE' });
    if (result.ok) {
      setCustomers(customers.filter((customer) => customer.id !== archivingCustomerId));
      notify('Customer archived');
      closeArchiveCustomer();
    }
  };

  useEffect(() => {
    if (
      !token
      || (!showPatrolModal && !showEditPatrolModal)
      || !patrolForm.start_time
      || !patrolForm.end_time
      || new Date(patrolForm.end_time) <= new Date(patrolForm.start_time)
    ) {
      setAvailability(null);
      return;
    }
    let active = true;
    const loadAvailability = async () => {
      setAvailabilityLoading(true);
      const params = new URLSearchParams({
        start_time: new Date(patrolForm.start_time).toISOString(),
        end_time: new Date(patrolForm.end_time).toISOString(),
        required_officers: String(patrolForm.required_officers || 1),
      });
      if (editingPatrolId) params.set('exclude_patrol_id', String(editingPatrolId));
      const result = await apiCall(`${API_BASE}/teams/availability?${params}`, { method: 'GET' });
      if (active && result.ok) setAvailability(result.data);
      if (active) setAvailabilityLoading(false);
    };
    loadAvailability();
    return () => { active = false; };
  }, [
    token,
    showPatrolModal,
    showEditPatrolModal,
    patrolForm.start_time,
    patrolForm.end_time,
    patrolForm.required_officers,
    editingPatrolId,
  ]);

  useEffect(() => {
    if (!token || !authContext) return;
    if (canAccessPage('dashboard', authContext.permissions)) loadDashboardStats();
    if (canAccessPage('patrols', authContext.permissions)) loadPatrols();
    if (canAccessPage('incidents', authContext.permissions)) loadIncidents();
    if (canAccessPage('checkpoints', authContext.permissions)) loadCheckpoints();
    if (canAccessPage('officers', authContext.permissions)) loadOfficers();
    if (canAccessPage('teams', authContext.permissions)) loadTeams();
    if (canAccessPage('my-team', authContext.permissions)) loadMyTeam();
    if (canAccessPage('vehicles', authContext.permissions)) loadVehicles();
    if (canAccessPage('customers', authContext.permissions)) loadCustomers();
  }, [token, authContext]);

  const permissions = useMemo(() => authContext?.permissions || [], [authContext]);
  const visibleNavItems = useMemo(() => visibleNavigation(permissions), [permissions]);
  const isAuthenticated = Boolean(token && authContext);
  const activePageLabel = visibleNavItems.find((item) => item.id === activeNav)?.label || 'PatrolPro';
  const closeMobileNav = useCallback(() => {
    setMobileNavOpen(false);
    window.requestAnimationFrame(() => mobileMenuButtonRef.current?.focus());
  }, []);
  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
    } finally {
      setToken('');
      setAuthContext(null);
      setMobileNavOpen(false);
      notify('Logged out');
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    const activeExists = visibleNavItems.some((item) => item.id === activeNav);
    if (!activeExists && visibleNavItems.length > 0) {
      setActiveNav(visibleNavItems[0].id);
    }
  }, [isAuthenticated, activeNav, visibleNavItems]);

  useEffect(() => {
    const desktopQuery = window.matchMedia('(min-width: 1024px)');
    const closeDrawerOnDesktop = (event) => {
      if (event.matches) setMobileNavOpen(false);
    };
    desktopQuery.addEventListener?.('change', closeDrawerOnDesktop);
    return () => desktopQuery.removeEventListener?.('change', closeDrawerOnDesktop);
  }, []);

  // Sidebar
  const Sidebar = () => {
    const { colors } = useTheme();
    return (
    <div className="pp-desktop-sidebar" style={{
      width: sidebarOpen ? 280 : 80,
      background: colors.sidebarBg,
      color: colors.sidebarText,
      padding: spacing.lg,
      flexDirection: 'column',
      transition: transitions.base,
      borderRight: `1px solid ${colors.border}`,
      height: '100vh',
      overflowY: 'auto',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing.lg }}>
        {sidebarOpen && <h1 style={{ ...typography.headingMd, margin: 0, fontSize: 20, color: colors.sidebarText }}>PatrolPro</h1>}
        <button className="pp-icon-button" aria-label={sidebarOpen ? 'Collapse navigation' : 'Expand navigation'} aria-expanded={sidebarOpen} onClick={() => setSidebarOpen(!sidebarOpen)} style={{ background: 'transparent', border: 'none', color: colors.sidebarText, cursor: 'pointer', fontSize: 20 }}>
          <Icon name='menu' size={20} color={colors.sidebarText} />
        </button>
      </div>
      <nav style={{ flex: 1 }}>
        {visibleNavItems.map((item) => (
          <button
            key={item.id}
            aria-current={activeNav === item.id ? 'page' : undefined}
            onClick={() => setActiveNav(item.id)}
            style={{
              width: '100%', padding: spacing.md, marginBottom: spacing.sm,
              background: activeNav === item.id ? colors.rosePink : 'transparent',
              border: 'none', color: colors.sidebarText, borderRadius: radius.md,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: spacing.md,
              transition: transitions.fast, textAlign: 'left',
            }}
            onMouseEnter={(e) => { if (activeNav !== item.id) e.currentTarget.style.background = colors.slate300 + '33'; }}
            onMouseLeave={(e) => { if (activeNav !== item.id) e.currentTarget.style.background = 'transparent'; }}
          >
            <Icon name={item.icon} size={20} color={colors.sidebarText} />
            {sidebarOpen && <span>{item.label}</span>}
          </button>
        ))}
      </nav>
      <div style={{ paddingTop: spacing.lg, borderTop: `1px solid ${colors.border}` }}>
        {isAuthenticated && (
          <button onClick={handleLogout} style={{
            width: '100%', padding: spacing.md, background: 'transparent', border: 'none',
            color: colors.sidebarText, borderRadius: radius.md, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: spacing.md, transition: transitions.fast,
          }}>
            <Icon name='logout' size={20} color={colors.sidebarText} />
            {sidebarOpen && <span>Logout</span>}
          </button>
        )}
      </div>
    </div>
    );
  };

  // Top Navigation
  const TopNav = ({ darkMode, toggleDark }) => {
    const { colors } = useTheme();
    return (
    <div className="pp-top-nav" style={{
      background: colors.cardBg,
      borderBottom: `1px solid ${colors.border}`,
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <div className="pp-top-left" style={{ display: 'flex', alignItems: 'center', gap: spacing.md, flex: 1 }}>
        <button
          ref={mobileMenuButtonRef}
          className="pp-mobile-menu-button pp-icon-button"
          aria-label="Open navigation"
          aria-controls="mobile-navigation"
          aria-expanded={mobileNavOpen}
          onClick={() => setMobileNavOpen(true)}
          style={{ background: colors.lightGrey, border: `1px solid ${colors.border}`, borderRadius: radius.md, color: colors.slate900 }}
        >
          <Icon name="menu" size={20} />
        </button>
        <strong className="pp-mobile-title" style={{ ...typography.headingXs, color: colors.slate900 }}>
          {activePageLabel}
        </strong>
        <input
          className="pp-top-search"
          type='text'
          placeholder='Search patrols, incidents, officers...'
          style={{
            padding: spacing.md, border: `1px solid ${colors.border}`,
            borderRadius: radius.md, width: '100%', maxWidth: 400,
            ...typography.bodyMd, background: colors.pageBg, color: colors.slate900,
          }}
        />
      </div>
      <div className="pp-top-actions" style={{ display: 'flex', alignItems: 'center', gap: 'var(--pp-top-actions-gap)' }}>
        <button
          className="pp-icon-button"
          aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={toggleDark}
          title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          style={{ background: colors.lightGrey, border: `1px solid ${colors.border}`, borderRadius: radius.md, padding: `${spacing.xs} ${spacing.sm}`, cursor: 'pointer', fontSize: 18 }}
        >
          {darkMode ? '☀️' : '🌙'}
        </button>
        <button className="pp-top-notifications pp-icon-button" aria-label="Notifications" style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', opacity: 0.7 }}>
          <Icon name='bell' size={20} />
        </button>
        {token ? (
          <div className="pp-account" style={{ alignItems: 'center', gap: spacing.md }}>
            <div className="pp-avatar" aria-hidden="true" style={{ width: 'var(--pp-avatar-size)', height: 'var(--pp-avatar-size)', borderRadius: '50%', background: colors.rosePink, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>
              {email.charAt(0).toUpperCase()}
            </div>
            <div className="pp-account-copy">
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 600, color: colors.slate900 }}>{email.split('@')[0]}</p>
              <p style={{ ...typography.bodySm, margin: 0, color: colors.slate500, textTransform: 'capitalize' }}>
                {authContext?.role?.replaceAll('_', ' ')}
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
    );
  };

  // Officers Content
  const OfficersContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div className="pp-page-heading-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Officers</h1>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Manage your security officers and their assignments
        </p>
      </div>

      {officersLoading ? (
        <Card><p style={{ ...typography.bodyMd, color: colors.slate500 }}>Loading officers…</p></Card>
      ) : officersError ? (
        <Card><p role="alert" style={{ ...typography.bodyMd, color: colors.error }}>{officersError}</p></Card>
      ) : officers.length === 0 ? (
        <Card>
          <p style={{ ...typography.bodyMd, color: colors.slate500 }}>
            No officers yet. Secure user invitation delivery is not yet available.
          </p>
        </Card>
      ) : (
      <div className="pp-card-grid">
        {officers.map((officer) => (
          <Card key={officer.id} highlight>
            <h3 style={{ ...typography.headingSm, margin: 0, marginBottom: spacing.sm, color: colors.slate900 }}>
              {officer.full_name || officer.email}
            </h3>
            <div style={{ marginBottom: spacing.md }}>
              <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Email</p>
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 600, color: colors.slate900 }}>
                {officer.email}
              </p>
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: spacing.md,
              marginBottom: spacing.md,
              paddingBottom: spacing.md,
              borderBottom: `1px solid ${colors.border}`,
            }}>
              <div>
                <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Status</p>
                <Badge variant="success">Active</Badge>
              </div>
              <div>
                <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Role</p>
                <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 500 }}>{officer.role}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
      )}
    </div>
  );

  const TeamsContent = () => {
    const canManageTeams = (authContext?.permissions || []).includes('users.manage');
    const selectedMembers = officers.filter((officer) => (
      teamForm.member_user_ids.includes(officer.id)
    ));
    return (
      <div>
        <div className="pp-page-heading-row" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: spacing.lg }}>
          <div>
            <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Teams</h1>
            <p style={{ ...typography.bodyLg, color: colors.slate500 }}>
              Manage team membership, leadership, availability and deployments.
            </p>
          </div>
          {canManageTeams && (
            <Button icon="add" onClick={() => {
              setEditingTeamId(null);
              setTeamForm({
                name: '', leader_user_id: '', notes: '', status: 'active', member_user_ids: [],
              });
              setShowTeamModal(true);
            }}>Create Team</Button>
          )}
        </div>
        {teamsLoading ? <Card><p>Loading teams…</p></Card> : teams.length === 0 ? (
          <Card><p>No teams have been created.</p></Card>
        ) : (
          <div className="pp-card-grid">
            {teams.map((team) => (
              <Card key={team.id} highlight>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: spacing.sm }}>
                  <h3 style={{ ...typography.headingSm, margin: 0 }}>{team.name}</h3>
                  <Badge variant={team.availability === 'deployed' ? 'warning' : 'success'}>
                    {team.availability}
                  </Badge>
                </div>
                <p style={{ ...typography.bodySm, color: colors.slate500 }}>
                  {team.members.length} member(s) · {team.status}
                </p>
                <p style={{ ...typography.labelSm, marginBottom: spacing.xs }}>Members</p>
                {team.members.map((member) => (
                  <p key={member.id} style={{ ...typography.bodySm, margin: `${spacing.xs} 0` }}>
                    {member.full_name || 'Unnamed officer'} · {member.staff_identifier}
                    {member.id === team.leader_user_id ? ' · Team Leader' : ''}
                  </p>
                ))}
                {team.active_patrols.length > 0 && (
                  <p style={{ ...typography.bodySm }}>Deployed: {team.active_patrols.join(', ')}</p>
                )}
                {canManageTeams && (
                  <div className="pp-row-actions" style={{ display: 'flex', gap: spacing.sm }}>
                    <Button variant="secondary" size="sm" onClick={() => editTeam(team)}>Edit</Button>
                    <Button variant="danger" size="sm" onClick={() => archiveTeam(team)}>Archive</Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
        <Modal
          open={showTeamModal}
          onClose={() => setShowTeamModal(false)}
          title={editingTeamId ? 'Edit Team' : 'Create Team'}
        >
          <TextField
            label="Team Name"
            value={teamForm.name}
            onChange={(name) => setTeamForm({ ...teamForm, name })}
            placeholder="Team Alpha"
          />
          <SearchableMultiSelect
            label="Add Officers"
            options={officers.map((officer) => ({
              value: officer.id,
              label: `${officer.full_name || 'Unnamed officer'} · ${officer.staff_identifier}`,
            }))}
            selected={teamForm.member_user_ids}
            onChange={(member_user_ids) => {
              const leaderStillSelected = member_user_ids.includes(Number(teamForm.leader_user_id));
              setTeamForm({
                ...teamForm,
                member_user_ids,
                leader_user_id: leaderStillSelected ? teamForm.leader_user_id : '',
              });
            }}
          />
          <SelectField
            label="Team Leader"
            value={teamForm.leader_user_id}
            onChange={(leader_user_id) => setTeamForm({ ...teamForm, leader_user_id })}
            options={selectedMembers.map((officer) => ({
              value: officer.id,
              label: `${officer.full_name || 'Unnamed officer'} · ${officer.staff_identifier}`,
            }))}
            placeholder="Select a team member"
          />
          <SelectField
            label="Team Status"
            value={teamForm.status}
            onChange={(status) => setTeamForm({ ...teamForm, status })}
            options={[
              { value: 'active', label: 'Active' },
              { value: 'inactive', label: 'Inactive' },
            ]}
          />
          <TextField
            label="Team Notes"
            value={teamForm.notes}
            onChange={(notes) => setTeamForm({ ...teamForm, notes })}
            placeholder="Operational notes (optional)"
          />
          <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md }}>
            <Button variant="secondary" fullWidth onClick={() => setShowTeamModal(false)}>Cancel</Button>
            <Button fullWidth onClick={saveTeam}>{editingTeamId ? 'Save Team' : 'Create Team'}</Button>
          </div>
        </Modal>
      </div>
    );
  };

  const MyTeamContent = () => (
    <div>
      <h1 style={{ ...typography.headingXL, marginTop: 0, color: colors.slate900 }}>My Team</h1>
      {!myTeam ? (
        <Card><p>You are not currently assigned to a team.</p></Card>
      ) : (
        <Card highlight>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <h2 style={{ ...typography.headingMd, marginTop: 0 }}>{myTeam.name}</h2>
            <Badge variant={myTeam.availability === 'deployed' ? 'warning' : 'success'}>
              {myTeam.availability}
            </Badge>
          </div>
          <p style={{ ...typography.bodyMd, color: colors.slate500 }}>
            Use names and staff IDs to confirm coworker identity before deployment.
          </p>
          <EnterpriseTable
            columns={[
              { key: 'name', label: 'Coworker' },
              { key: 'staffId', label: 'Staff ID' },
              { key: 'role', label: 'Role' },
              { key: 'leader', label: 'Team Position' },
            ]}
            rows={myTeam.members.map((member) => ({
              id: member.id,
              cells: {
                name: member.full_name || 'Unnamed officer',
                staffId: member.staff_identifier,
                role: member.role,
                leader: member.id === myTeam.leader_user_id ? 'Team Leader' : 'Member',
              },
            }))}
          />
          {myTeam.active_patrols.length > 0 && (
            <p>Active patrols: {myTeam.active_patrols.join(', ')}</p>
          )}
        </Card>
      )}
    </div>
  );

  // Incidents Content
  const IncidentsContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div className="pp-page-heading-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Incidents</h1>
          {(authContext?.permissions || []).includes('incidents.create') && (
            <Button icon="add" onClick={() => {
              setIncidentForm(emptyIncidentForm);
              setShowIncidentModal(true);
            }}>Report Incident</Button>
          )}
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Track and manage security incidents
        </p>
      </div>

      <div className="pp-card-grid">
        {incidents.map((incident) => (
          <Card key={incident.id} highlight>
            <h3 style={{ ...typography.headingSm, margin: 0, marginBottom: spacing.sm, color: colors.slate900 }}>
              {incident.title}
            </h3>
            <div style={{ marginBottom: spacing.md }}>
              <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Location</p>
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 600, color: colors.slate900 }}>
                {incident.location}
              </p>
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: spacing.md,
              marginBottom: spacing.md,
              paddingBottom: spacing.md,
              borderBottom: `1px solid ${colors.border}`,
            }}>
              <div>
                <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Severity</p>
                <Badge variant={incident.severity === 'high' ? 'error' : incident.severity === 'medium' ? 'warning' : 'info'}>
                  {incident.severity}
                </Badge>
              </div>
              <div>
                <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Status</p>
                <Badge variant={incident.status === 'open' ? 'error' : incident.status === 'investigating' ? 'warning' : 'success'}>
                  {incident.status}
                </Badge>
              </div>
            </div>
            {(authContext?.permissions || []).includes('incidents.manage') && (
              <div className="pp-row-actions" style={{ display: 'flex', gap: spacing.sm }}>
                <Button variant="secondary" size="sm" fullWidth icon="edit" onClick={() => startEditIncident(incident)}>Edit</Button>
                <Button variant="danger" size="sm" fullWidth icon="trash" onClick={() => requestRemoveIncident(incident.id)}>Archive</Button>
              </div>
            )}
          </Card>
        ))}
      </div>

      <Modal open={showIncidentModal} onClose={() => setShowIncidentModal(false)} title="Report Incident">
        <TextField label="Title" value={incidentForm.title} onChange={(title) => setIncidentForm({ ...incidentForm, title })} placeholder="Concise incident title" />
        <TextField label="Description" value={incidentForm.description} onChange={(description) => setIncidentForm({ ...incidentForm, description })} placeholder="What happened? Include observable facts." />
        <SelectField
          label="Category"
          value={incidentForm.category}
          onChange={(category) => setIncidentForm({ ...incidentForm, category })}
          options={[
            ['security', 'Security'], ['safety', 'Safety'], ['access_control', 'Access Control'],
            ['theft', 'Theft'], ['vandalism', 'Vandalism'], ['medical', 'Medical'], ['other', 'Other'],
          ].map(([value, label]) => ({ value, label }))}
        />
        <TextField label="Location" value={incidentForm.location} onChange={(location) => setIncidentForm({ ...incidentForm, location })} placeholder="Exact site location" />
        <SelectField
          label="Related Patrol"
          value={incidentForm.patrol_id}
          onChange={(patrol_id) => setIncidentForm({ ...incidentForm, patrol_id })}
          options={patrols.map((patrol) => ({ value: patrol.id, label: patrol.name }))}
          placeholder="No related patrol"
        />
        <SelectField
          label="Severity"
          value={incidentForm.severity}
          onChange={(severity) => setIncidentForm({ ...incidentForm, severity })}
          options={['low', 'medium', 'high', 'critical'].map((value) => ({ value, label: value }))}
        />
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md }}>
          <Button variant="secondary" fullWidth onClick={() => setShowIncidentModal(false)}>Cancel</Button>
          <Button fullWidth onClick={handleCreateIncident}>Report Incident</Button>
        </div>
      </Modal>

      <Modal open={showEditIncidentModal} onClose={closeEditIncident} title="Edit Incident">
        <TextField
          label="Title"
          value={incidentForm.title}
          onChange={(v) => setIncidentForm({ ...incidentForm, title: v })}
          placeholder="Incident title"
          autoFocus={true}
        />
        <TextField
          label="Location"
          value={incidentForm.location}
          onChange={(v) => setIncidentForm({ ...incidentForm, location: v })}
          placeholder="Incident location"
        />
        <TextField label="Description" value={incidentForm.description} onChange={(description) => setIncidentForm({ ...incidentForm, description })} placeholder="Observable facts" />
        <SelectField label="Category" value={incidentForm.category} onChange={(category) => setIncidentForm({ ...incidentForm, category })} options={[
          ['security', 'Security'], ['safety', 'Safety'], ['access_control', 'Access Control'],
          ['theft', 'Theft'], ['vandalism', 'Vandalism'], ['medical', 'Medical'], ['other', 'Other'],
        ].map(([value, label]) => ({ value, label }))} />
        <SelectField label="Severity" value={incidentForm.severity} onChange={(severity) => setIncidentForm({ ...incidentForm, severity })} options={['low', 'medium', 'high', 'critical'].map((value) => ({ value, label: value }))} />
        <SelectField label="Status" value={incidentForm.status} onChange={(status) => setIncidentForm({ ...incidentForm, status })} options={['open', 'investigating', 'resolved', 'cancelled'].map((value) => ({ value, label: value }))} />
        {(incidentForm.status === 'resolved' || incidentForm.status === 'cancelled') && (
          <TextField label="Resolution Notes" value={incidentForm.resolution_notes} onChange={(resolution_notes) => setIncidentForm({ ...incidentForm, resolution_notes })} placeholder="Required: explain the outcome" />
        )}
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button onClick={closeEditIncident} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={handleUpdateIncident} fullWidth>Save Changes</Button>
        </div>
      </Modal>

      <Modal open={showRemoveIncidentModal} onClose={closeRemoveIncident} title="Remove Incident">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>
          Are you sure you want to remove this incident?
        </p>
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md }}>
          <Button onClick={closeRemoveIncident} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={confirmRemoveIncident} variant="danger" fullWidth>Remove</Button>
        </div>
      </Modal>
    </div>
  );

  // Checkpoints Content
  const CheckpointsContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div className="pp-page-heading-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Checkpoints</h1>
          {(authContext?.permissions || []).includes('checkpoints.manage') && (
            <Button icon="add" onClick={() => {
              setCheckpointForm({
                ...emptyCheckpointForm,
                code: `CP-${String(Date.now()).slice(-8)}`,
              });
              setShowCheckpointModal(true);
            }}>Add Checkpoint</Button>
          )}
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Manage patrol checkpoints and low-assurance code confirmations.
        </p>
      </div>

      <div className="pp-card-grid">
        {checkpoints.map((checkpoint) => (
          <Card key={checkpoint.id} highlight>
            <h3 style={{ ...typography.headingSm, margin: 0, marginBottom: spacing.sm, color: colors.slate900 }}>
              {checkpoint.name}
            </h3>
            <div style={{ marginBottom: spacing.md }}>
              <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Location</p>
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 600, color: colors.slate900 }}>
                {checkpoint.location_label || 'Not set'}
              </p>
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: spacing.md,
              marginBottom: spacing.md,
              paddingBottom: spacing.md,
              borderBottom: `1px solid ${colors.border}`,
            }}>
              <div>
                <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Status</p>
                <Badge variant={checkpoint.status === 'active' ? 'success' : 'warning'}>
                  {checkpointStatusLabel(checkpoint.status)}
                </Badge>
              </div>
              <div>
                <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Code confirmation</p>
                <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 500 }}>
                  {checkpoint.verified_at ? `Accepted ${formatDateTime(checkpoint.verified_at)}` : 'Not confirmed'}
                </p>
              </div>
            </div>
            {(authContext?.permissions || []).includes('checkpoints.manage') && checkpoint.status !== 'verified' && (
              <div className="pp-row-actions" style={{ display: 'flex', gap: spacing.sm }}>
                <Button variant="secondary" size="sm" fullWidth icon="edit" onClick={() => startEditCheckpoint(checkpoint)}>Edit</Button>
                <Button variant="danger" size="sm" fullWidth icon="trash" onClick={() => requestRemoveCheckpoint(checkpoint.id)}>Archive</Button>
              </div>
            )}
            {(authContext?.permissions || []).includes('checkpoints.verify') && checkpoint.status === 'pending' && (
              <Button size="sm" fullWidth onClick={() => {
                setVerifyingCheckpoint(checkpoint);
                setVerificationCode('');
              }}>{CHECKPOINT_CONFIRMATION_COPY.action}</Button>
            )}
          </Card>
        ))}
      </div>

      <Modal open={showCheckpointModal} onClose={() => setShowCheckpointModal(false)} title="Add Checkpoint">
        <TextField label="Checkpoint Name" value={checkpointForm.name} onChange={(name) => setCheckpointForm({ ...checkpointForm, name })} placeholder="North Gate" />
        <TextField label="Checkpoint Code" value={checkpointForm.code} onChange={(code) => setCheckpointForm({ ...checkpointForm, code: code.toUpperCase() })} placeholder="Generated automatically" />
        <SelectField label="Patrol" value={checkpointForm.patrol_id} onChange={(patrol_id) => setCheckpointForm({ ...checkpointForm, patrol_id })} options={patrols.map((patrol) => ({ value: patrol.id, label: patrol.name }))} placeholder="Select a patrol (optional)" />
        <TextField label="Location" value={checkpointForm.location_label} onChange={(location_label) => setCheckpointForm({ ...checkpointForm, location_label })} placeholder="Exact checkpoint location" />
        <TextField label="NFC Tag" value={checkpointForm.nfc_tag} onChange={(nfc_tag) => setCheckpointForm({ ...checkpointForm, nfc_tag })} placeholder="Optional scanned tag" />
        <SelectField label="Status" value={checkpointForm.status} onChange={(status) => setCheckpointForm({ ...checkpointForm, status })} options={[
          { value: 'pending', label: 'Pending' },
          { value: 'inactive', label: 'Inactive' },
        ]} />
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md }}>
          <Button variant="secondary" fullWidth onClick={() => setShowCheckpointModal(false)}>Cancel</Button>
          <Button fullWidth onClick={handleCreateCheckpoint}>Create Checkpoint</Button>
        </div>
      </Modal>

      <Modal open={showEditCheckpointModal} onClose={closeEditCheckpoint} title="Edit Checkpoint">
        <TextField
          label="Name"
          value={checkpointForm.name}
          onChange={(v) => setCheckpointForm({ ...checkpointForm, name: v })}
          placeholder="Checkpoint name"
          autoFocus={true}
        />
        <TextField label="Checkpoint Code" value={checkpointForm.code} onChange={(code) => setCheckpointForm({ ...checkpointForm, code: code.toUpperCase() })} />
        <SelectField label="Patrol" value={checkpointForm.patrol_id} onChange={(patrol_id) => setCheckpointForm({ ...checkpointForm, patrol_id })} options={patrols.map((patrol) => ({ value: patrol.id, label: patrol.name }))} placeholder="Select a patrol (optional)" />
        <TextField label="Location" value={checkpointForm.location_label} onChange={(location_label) => setCheckpointForm({ ...checkpointForm, location_label })} placeholder="Exact checkpoint location" />
        <TextField label="NFC Tag" value={checkpointForm.nfc_tag} onChange={(nfc_tag) => setCheckpointForm({ ...checkpointForm, nfc_tag })} placeholder="Optional scanned tag" />
        <SelectField label="Status" value={checkpointForm.status} onChange={(status) => setCheckpointForm({ ...checkpointForm, status })} options={[
          { value: 'pending', label: 'Pending' },
          { value: 'inactive', label: 'Inactive' },
        ]} />
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button onClick={closeEditCheckpoint} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={handleUpdateCheckpoint} fullWidth>Save Changes</Button>
        </div>
      </Modal>

      <Modal
        open={Boolean(verifyingCheckpoint)}
        onClose={() => setVerifyingCheckpoint(null)}
        title="Confirm Checkpoint Code"
      >
        <p style={{ ...typography.bodyMd }}>
          Enter the displayed code at {verifyingCheckpoint?.location_label}. This is a{' '}
          {CHECKPOINT_CONFIRMATION_COPY.assurance.toLowerCase()} and does not independently
          prove physical presence.
        </p>
        <TextField
          label="Checkpoint Code"
          value={verificationCode}
          onChange={(value) => setVerificationCode(value.toUpperCase())}
          placeholder="Enter or scan checkpoint code"
        />
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md }}>
          <Button variant="secondary" fullWidth onClick={() => setVerifyingCheckpoint(null)}>Cancel</Button>
          <Button fullWidth onClick={verifyCheckpoint}>Submit Code</Button>
        </div>
      </Modal>

      <Modal open={showRemoveCheckpointModal} onClose={closeRemoveCheckpoint} title="Remove Checkpoint">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>
          Are you sure you want to remove this checkpoint?
        </p>
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md }}>
          <Button onClick={closeRemoveCheckpoint} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={confirmRemoveCheckpoint} variant="danger" fullWidth>Remove</Button>
        </div>
      </Modal>
    </div>
  );

  const AnalyticsContent = () => {
    const openIncidents = incidents.filter((i) => i.status === 'open').length;
    const activeCheckpoints = checkpoints.filter((c) => c.status === 'active').length;
    const onDutyOfficers = officers.filter((o) => o.status === 'On Duty').length;

    return (
      <div>
        <div style={{ marginBottom: spacing.lg }}>
          <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>Analytics</h1>
          <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
            Real-time metrics for patrol activity, staffing, and incident response.
          </p>
        </div>

        <div className="pp-stats-grid" style={{ marginBottom: spacing.lg }}>
          <KPICard title="Open Incidents" value={String(openIncidents)} subtitle="Needs active follow-up" icon="incidents" color={colors.error} />
          <KPICard title="On-Duty Officers" value={String(onDutyOfficers)} subtitle="Currently active" icon="officers" color={colors.success} />
          <KPICard title="Active Checkpoints" value={String(activeCheckpoints)} subtitle="Configured checkpoints" icon="checkpoints" color={colors.blushPink} />
          <KPICard title="Stored Vehicles" value={String(vehicles.length)} subtitle="Tracked units" icon="vehicles" color={colors.warning} />
        </div>

        <Card header="Zone Load Overview">
          <EnterpriseTable
            columns={[
              { key: 'zone', label: 'Zone' },
              { key: 'count', label: 'Assigned Officers' },
              { key: 'status', label: 'Status' },
            ]}
            rows={['Zone A', 'Zone B', 'Zone C'].map((zone) => {
              const count = officers.filter((o) => o.zone === zone).length;
              return { cells: { zone, count: String(count), status: count > 0 ? 'covered' : 'unassigned' } };
            })}
            pageSize={10}
          />
        </Card>
      </div>
    );
  };

  const VehiclesContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div className="pp-page-heading-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Vehicles</h1>
          <div className="pp-page-actions" style={{ display: 'flex', gap: spacing.md }}>
            <Button variant="secondary" icon="load" onClick={loadVehicles}>Refresh</Button>
            <Button icon="add" onClick={() => setShowVehicleModal(true)}>Add Vehicle</Button>
          </div>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Fleet and device tracking for patrol units.
        </p>
      </div>

      <Card header="Tracked Vehicles">
        <EnterpriseTable
          columns={[
            { key: 'name', label: 'Unit Name' },
            { key: 'serial', label: 'Unit ID' },
            { key: 'status', label: 'Status' },
          ]}
          rows={vehicles.map((v) => ({
            cells: { name: v.name, serial: v.serial_number, status: v.status },
            id: v.id, raw: v,
          }))}
          actions={(row) => (
            <>
              <Button size="sm" variant="secondary" icon="edit" onClick={() => startEditVehicle(row.raw)}>Edit</Button>
              <Button size="sm" variant="danger" icon="trash" onClick={() => requestRemoveVehicle(row.id)}>Remove</Button>
            </>
          )}
        />
      </Card>

      <Modal open={showVehicleModal} onClose={() => setShowVehicleModal(false)} title="Add Vehicle">
        <TextField label="Unit Name" value={vehicleForm.name} onChange={(v) => setVehicleForm({ ...vehicleForm, name: v })} placeholder="Patrol SUV 01" autoFocus={true} />
        <TextField label="Unit ID" value={vehicleForm.serial_number} onChange={(v) => setVehicleForm({ ...vehicleForm, serial_number: v })} placeholder="SUV-01" />
        <TextField label="Status" value={vehicleForm.status} onChange={(v) => setVehicleForm({ ...vehicleForm, status: v })} placeholder="active | maintenance" />
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={() => setShowVehicleModal(false)}>Cancel</Button>
          <Button fullWidth onClick={handleCreateVehicle}>Create</Button>
        </div>
      </Modal>

      <Modal open={showEditVehicleModal} onClose={closeEditVehicle} title="Edit Vehicle">
        <TextField label="Unit Name" value={vehicleForm.name} onChange={(v) => setVehicleForm({ ...vehicleForm, name: v })} placeholder="Patrol SUV 01" autoFocus={true} />
        <TextField label="Unit ID" value={vehicleForm.serial_number} onChange={(v) => setVehicleForm({ ...vehicleForm, serial_number: v })} placeholder="SUV-01" />
        <TextField label="Status" value={vehicleForm.status} onChange={(v) => setVehicleForm({ ...vehicleForm, status: v })} placeholder="active | maintenance" />
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={closeEditVehicle}>Cancel</Button>
          <Button fullWidth onClick={handleUpdateVehicle}>Save</Button>
        </div>
      </Modal>

      <Modal open={showRemoveVehicleModal} onClose={closeRemoveVehicle} title="Remove Vehicle">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>Are you sure you want to remove this vehicle?</p>
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md }}>
          <Button variant="secondary" fullWidth onClick={closeRemoveVehicle}>Cancel</Button>
          <Button variant="danger" fullWidth onClick={confirmRemoveVehicle}>Remove</Button>
        </div>
      </Modal>
    </div>
  );

  const UsersContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>
          Users
        </h1>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Secure email invitation delivery is not yet available.
        </p>
      </div>
      <Card header="User invitations unavailable">
        <p style={{ ...typography.bodyMd, color: colors.slate700, margin: 0 }}>
          No invitation has been sent. User invitations will be enabled when Patrol Pro can
          deliver single-use links securely and report their delivery status accurately.
        </p>
      </Card>
    </div>
  );

  // Main Content
  const renderContent = () => {
    if (!token) return (
      <AuthContent 
        authTab={authTab} 
        setAuthTab={setAuthTab}
        email={email} 
        setEmail={setEmail}
        password={password} 
        setPassword={setPassword}
        fullName={fullName} 
        setFullName={setFullName}
        companyName={companyName}
        setCompanyName={setCompanyName}
        handleLogin={handleLogin} 
        handleRegister={handleRegister}
      />
    );

    if (!authContext) {
      return (
        <Card>
          <p style={{ ...typography.bodyMd, color: colors.slate500 }}>Loading account permissions...</p>
        </Card>
      );
    }

    if (!canAccessPage(activeNav, permissions)) {
      return (
        <Card>
          <h1 style={{ ...typography.headingLg, color: colors.slate900 }}>Access denied</h1>
          <p style={{ ...typography.bodyMd, color: colors.slate500 }}>
            Your account does not have permission to view this page.
          </p>
        </Card>
      );
    }

    switch (activeNav) {
      case 'dashboard':
        return <DashboardContent stats={dashboardStats} isLoading={dashboardLoading} error={dashboardError} />;
      case 'patrols':
        return (
          <PatrolsContent 
            patrols={patrols}
            patrolForm={patrolForm}
            setPatrolForm={setPatrolForm}
            showPatrolModal={showPatrolModal}
            setShowPatrolModal={setShowPatrolModal}
            showEditPatrolModal={showEditPatrolModal}
            startEditPatrol={startEditPatrol}
            handleDeletePatrol={handleDeletePatrol}
            onCloseEditPatrol={closeEditPatrol}
            handleCreatePatrol={handleCreatePatrol}
            handleUpdatePatrol={handleUpdatePatrol}
            loadPatrols={loadPatrols}
            availability={availability}
            availabilityLoading={availabilityLoading}
          />
        );
      case 'officers':
        return <OfficersContent />;
      case 'teams':
        return <TeamsContent />;
      case 'my-team':
        return <MyTeamContent />;
      case 'incidents':
        return <IncidentsContent />;
      case 'checkpoints':
        return <CheckpointsContent />;
      case 'reports':
        return <ReportsPage colors={colors} spacing={spacing} typography={typography} />;
      case 'analytics':
        return <AnalyticsContent />;
      case 'vehicles':
        return <VehiclesContent />;
      case 'customers':
        return (
          <CustomersPage
            customers={customers}
            customerForm={customerForm}
            setCustomerForm={setCustomerForm}
            showCreate={showCustomerModal}
            setShowCreate={setShowCustomerModal}
            showEdit={showEditCustomerModal}
            closeEdit={closeEditCustomer}
            showArchive={showArchiveCustomerModal}
            closeArchive={closeArchiveCustomer}
            loadCustomers={loadCustomers}
            createCustomer={handleCreateCustomer}
            updateCustomer={handleUpdateCustomer}
            startEdit={startEditCustomer}
            requestArchive={requestArchiveCustomer}
            confirmArchive={confirmArchiveCustomer}
            ui={{ Button, Card, EnterpriseTable, Modal, TextField }}
            design={{ colors, spacing, typography }}
          />
        );
      case 'users':
        return <UsersContent />;
      case 'settings':
        return <SettingsPage colors={colors} spacing={spacing} typography={typography} />;
      default:
        return (
          <div>
            <h1 style={{ ...typography.headingXL, color: colors.slate900 }}>
              {visibleNavItems.find((n) => n.id === activeNav)?.label}
            </h1>
            <Card>
              <p style={{ ...typography.bodyLg, color: colors.slate500 }}>
                This page is unavailable.
              </p>
            </Card>
          </div>
        );
    }
  };

  return (
    <div className="pp-app-shell" style={{
      display: 'flex',
      minHeight: '100dvh',
      height: '100dvh',
      background: colors.pageBg,
      fontFamily: '"Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", sans-serif',
      color: colors.slate900,
    }}>
      {isAuthenticated && <Sidebar />}
      {isAuthenticated && (
        <MobileNavigation
          open={mobileNavOpen}
          items={visibleNavItems}
          activeNav={activeNav}
          onSelect={setActiveNav}
          onClose={closeMobileNav}
          onLogout={handleLogout}
        />
      )}

      <div className="pp-app-column" style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {isAuthenticated && <TopNav darkMode={dark} toggleDark={toggle} />}

        <main className="pp-main" style={{
          flex: 1,
          overflow: 'auto',
          padding: 'var(--pp-content-padding)',
          background: colors.pageBg,
        }}>
          {renderContent()}
        </main>
      </div>

      {notification && (
        <Notification
          message={notification.message}
          type={notification.type}
          onClose={() => setNotification(null)}
        />
      )}

      <style>{`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        button:focus { outline: 2px solid ${colors.rosePink}; outline-offset: 2px; }
        input:focus, select:focus { outline: none; }
        @keyframes slideIn {
          from { transform: translateX(400px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes skeletonShimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: ${colors.lightGrey}; }
        ::-webkit-scrollbar-thumb { background: ${colors.slate300}; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: ${colors.slate400}; }
      `}</style>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppInner />
    </ThemeProvider>
  );
}
