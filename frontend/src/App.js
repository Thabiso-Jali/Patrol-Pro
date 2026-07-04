import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { lightTokens, darkTokens, spacing, radius, typography, shadows, transitions } from './theme';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

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
    communications: '💬', documents: '📄', users: '👥', settings: '⚙️',
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
    <div style={{ background: colors.cardBg, borderRadius: radius.lg, padding: spacing.lg, border: `1px solid ${colors.border}` }}>
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

const Button = ({ children, variant = 'primary', size = 'md', disabled = false, icon, fullWidth = false, ...props }) => {
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
    <button style={style} disabled={disabled} {...props}>
      {icon && <Icon name={icon} size={16} />}
      {children}
    </button>
  );
};

const Card = ({ children, header, actions, highlight = false }) => {
  const { colors } = useTheme();
  return (
    <div style={{
      background: colors.white,
      borderRadius: radius.lg,
      padding: spacing.lg,
      boxShadow: highlight ? shadows.md : shadows.xs,
      border: `1px solid ${colors.border}`,
      transition: transitions.base,
    }}>
      {header && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: spacing.md,
          paddingBottom: spacing.md,
          borderBottom: `1px solid ${colors.border}`,
        }}>
          <h3 style={{ ...typography.headingSm, margin: 0, color: colors.slate900 }}>{header}</h3>
          {actions && <div style={{ display: 'flex', gap: spacing.sm }}>{actions}</div>}
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

const KPICard = ({ title, value, subtitle, trend, icon, color }) => {
  const { colors } = useTheme();
  const resolvedColor = color || colors.rosePink;
  return (
    <Card highlight>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <p style={{ ...typography.bodySm, color: colors.slate500, margin: 0, marginBottom: spacing.sm }}>{title}</p>
          <h2 style={{ ...typography.headingLg, margin: 0, color: colors.slate900 }}>{value}</h2>
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
          <div style={{
            width: 56, height: 56, background: `${resolvedColor}20`, borderRadius: radius.lg,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28,
          }}>
            <Icon name={icon} size={28} />
          </div>
        )}
      </div>
    </Card>
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
    <div>
      <div style={{ display: 'flex', gap: spacing.md, marginBottom: spacing.md, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type='text'
          placeholder='Filter rows...'
          value={filter}
          onChange={(e) => { setFilter(e.target.value); setPage(1); }}
          style={{
            padding: `${spacing.sm} ${spacing.md}`, border: `1px solid ${colors.border}`, borderRadius: radius.md,
            ...typography.bodyMd, flex: 1, minWidth: 200, maxWidth: 320, background: colors.cardBg, color: colors.slate900,
          }}
        />
        <span style={{ ...typography.bodySm, color: colors.slate500 }}>
          {sorted.length} row{sorted.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: typography.bodyMd.fontSize }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${colors.border}`, background: colors.lightGrey }}>
              {columns.map(({ key, label, sortable = true }) => (
                <th
                  key={key}
                  onClick={() => sortable && handleSort(key)}
                  style={{
                    padding: spacing.md, textAlign: 'left', ...typography.labelMd, color: colors.slate700, fontWeight: 600,
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
              <tr><td colSpan={columns.length + (actions ? 1 : 0)} style={{ padding: spacing.lg, textAlign: 'center', color: colors.slate500 }}>No results</td></tr>
            )}
            {paginated.map((row, i) => (
              <tr key={i}
                style={{ borderBottom: `1px solid ${colors.border}`, transition: transitions.fast }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.softPink}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                {columns.map(({ key }) => (
                  <td key={key} style={{ padding: spacing.md, ...typography.bodyMd, color: colors.slate700 }}>
                    {row.cells?.[key] ?? ''}
                  </td>
                ))}
                {actions && <td style={{ padding: spacing.md }}><div style={{ display: 'flex', gap: spacing.sm }}>{actions(row)}</div></td>}
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
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050 }}
      onClick={handleBackdropClick} onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div style={{ background: colors.cardBg, borderRadius: radius.lg, padding: spacing.lg, maxWidth: 520, width: '90%', boxShadow: shadows.xl, maxHeight: '90vh', overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg }}>
          <h2 style={{ ...typography.headingMd, margin: 0, color: colors.slate900 }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: colors.slate500 }}>
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
    <div style={{
      position: 'fixed',
      bottom: spacing.lg,
      right: spacing.lg,
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

// ==================== AUTH CONTENT COMPONENT ====================

const AuthContent = ({ 
  authTab, setAuthTab, 
  email, setEmail, 
  password, setPassword, 
  fullName, setFullName, 
  handleLogin, handleRegister 
}) => {
  const { colors } = useTheme();
  return (
  <div style={{ maxWidth: 500, margin: '0 auto', paddingTop: spacing.xl }}>
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
          <TextField label="Email" value={email} onChange={setEmail} placeholder="admin@security.com" autoFocus={true} />
          <TextField label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" />
          <Button onClick={handleLogin} fullWidth>Sign In</Button>
        </>
      ) : (
        <>
          <TextField label="Full Name" value={fullName} onChange={setFullName} placeholder="John Doe" autoFocus={true} />
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
}) => {
  const { colors } = useTheme();
  return (
  <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg }}>
      <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Patrols</h1>
      <div style={{ display: 'flex', gap: spacing.md }}>
        <Button onClick={loadPatrols} variant="secondary" icon="load">Refresh</Button>
        <Button onClick={() => setShowPatrolModal(true)} icon="add">New Patrol</Button>
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
        label="Assigned To"
        value={patrolForm.assigned_to}
        onChange={(v) => setPatrolForm({ ...patrolForm, assigned_to: v })}
        placeholder="Officer or team name"
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
      <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
        <Button onClick={() => setShowPatrolModal(false)} variant="secondary" fullWidth>Cancel</Button>
        <Button onClick={handleCreatePatrol} fullWidth>Create Patrol</Button>
      </div>
    </Modal>

    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
      gap: spacing.lg,
    }}>
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
              {patrol.assigned_to}
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
          <div style={{ display: 'flex', gap: spacing.sm }}>
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
          <Button onClick={() => setShowPatrolModal(true)} icon="add">Create First Patrol</Button>
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
          label="Assigned To"
          value={patrolForm.assigned_to}
          onChange={(v) => setPatrolForm({ ...patrolForm, assigned_to: v })}
          placeholder="Officer or team name"
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
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button onClick={onCloseEditPatrol} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={handleUpdatePatrol} fullWidth>Update Patrol</Button>
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
  const [token, setToken] = useState('');
  const [userRole, setUserRole] = useState('officer');
  const [notification, setNotification] = useState(null);

  // Auth state
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [authTab, setAuthTab] = useState('login');

  // Patrols
  const [patrols, setPatrols] = useState([]);
  const [patrolForm, setPatrolForm] = useState({ name: '', description: '', assigned_to: '', start_time: '', end_time: '' });
  const [showPatrolModal, setShowPatrolModal] = useState(false);
  const [showEditPatrolModal, setShowEditPatrolModal] = useState(false);
  const [editingPatrolId, setEditingPatrolId] = useState(null);

  // Officers
  const [officers, setOfficers] = useState([
    { id: 1, name: 'James Wilson', badge: 'P-001', status: 'On Duty', zone: 'Zone A' },
    { id: 2, name: 'Sarah Chen', badge: 'P-002', status: 'On Duty', zone: 'Zone B' },
    { id: 3, name: 'Marcus Johnson', badge: 'P-003', status: 'Break', zone: 'Zone C' },
  ]);
  const [officerForm, setOfficerForm] = useState({ name: '', badge: '', status: '', zone: '' });
  const [showEditOfficerModal, setShowEditOfficerModal] = useState(false);
  const [editingOfficerId, setEditingOfficerId] = useState(null);
  const [showRemoveOfficerModal, setShowRemoveOfficerModal] = useState(false);
  const [removingOfficerId, setRemovingOfficerId] = useState(null);

  // Incidents
  const [incidents, setIncidents] = useState([
    { id: 1, title: 'Door Forced Open', location: 'Warehouse C', severity: 'high', status: 'open', time: new Date() },
    { id: 2, title: 'Motion Detected', location: 'Parking Area B', severity: 'medium', status: 'investigating', time: new Date() },
  ]);
  const [incidentForm, setIncidentForm] = useState({ title: '', location: '', severity: '', status: '' });
  const [showEditIncidentModal, setShowEditIncidentModal] = useState(false);
  const [editingIncidentId, setEditingIncidentId] = useState(null);
  const [showRemoveIncidentModal, setShowRemoveIncidentModal] = useState(false);
  const [removingIncidentId, setRemovingIncidentId] = useState(null);

  // Checkpoints
  const [checkpoints, setCheckpoints] = useState([
    { id: 1, name: 'Main Gate', zone: 'North Perimeter', status: 'active', lastCheck: new Date() },
    { id: 2, name: 'Side Entrance', zone: 'East Perimeter', status: 'active', lastCheck: new Date() },
    { id: 3, name: 'Warehouse Door', zone: 'South Perimeter', status: 'inactive', lastCheck: new Date() },
  ]);
  const [checkpointForm, setCheckpointForm] = useState({ name: '', zone: '', status: '', lastCheck: '' });
  const [showEditCheckpointModal, setShowEditCheckpointModal] = useState(false);
  const [editingCheckpointId, setEditingCheckpointId] = useState(null);
  const [showRemoveCheckpointModal, setShowRemoveCheckpointModal] = useState(false);
  const [removingCheckpointId, setRemovingCheckpointId] = useState(null);

  // Users
  const [users, setUsers] = useState([]);

  // Reports
  const [reports, setReports] = useState([
    { id: 1, title: 'Daily Security Summary', range: 'Last 24 hours', generated_at: new Date(), status: 'ready' },
  ]);

  // Vehicles (backed by devices API)
  const [vehicles, setVehicles] = useState([]);
  const [vehicleForm, setVehicleForm] = useState({ name: '', serial_number: '', status: 'active' });
  const [showVehicleModal, setShowVehicleModal] = useState(false);
  const [showEditVehicleModal, setShowEditVehicleModal] = useState(false);
  const [editingVehicleId, setEditingVehicleId] = useState(null);
  const [showRemoveVehicleModal, setShowRemoveVehicleModal] = useState(false);
  const [removingVehicleId, setRemovingVehicleId] = useState(null);

  // Communications (backed by alerts API)
  const [communications, setCommunications] = useState([]);
  const [communicationForm, setCommunicationForm] = useState({ title: '', description: '', severity: 'medium', status: 'open' });
  const [showCommunicationModal, setShowCommunicationModal] = useState(false);
  const [showEditCommunicationModal, setShowEditCommunicationModal] = useState(false);
  const [editingCommunicationId, setEditingCommunicationId] = useState(null);
  const [showRemoveCommunicationModal, setShowRemoveCommunicationModal] = useState(false);
  const [removingCommunicationId, setRemovingCommunicationId] = useState(null);

  // Documents (backed by customers API)
  const [documents, setDocuments] = useState([]);
  const [documentForm, setDocumentForm] = useState({ name: '', contact_email: '', phone: '', address: '' });
  const [showDocumentModal, setShowDocumentModal] = useState(false);
  const [showEditDocumentModal, setShowEditDocumentModal] = useState(false);
  const [editingDocumentId, setEditingDocumentId] = useState(null);
  const [showRemoveDocumentModal, setShowRemoveDocumentModal] = useState(false);
  const [removingDocumentId, setRemovingDocumentId] = useState(null);

  // User management
  const [managedUsers, setManagedUsers] = useState([]);
  const [userForm, setUserForm] = useState({ email: '', full_name: '', password: '' });
  const [showUserModal, setShowUserModal] = useState(false);

  // Settings
  const [settingsForm, setSettingsForm] = useState({
    companyName: 'Patrol Pro Security',
    defaultShiftLength: '8',
    incidentEscalationMinutes: '15',
    emailNotifications: 'enabled',
  });

  const notify = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const headers = token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };

  const parseRoleFromToken = (jwtToken) => {
    try {
      const payloadBase64 = jwtToken.split('.')[1];
      const payload = JSON.parse(atob(payloadBase64));
      return payload?.role || 'officer';
    } catch {
      return 'officer';
    }
  };

  const apiCall = async (url, opts) => {
    try {
      const finalHeaders = { ...headers, ...opts.headers };
      const response = await fetch(url, { ...opts, headers: finalHeaders });
      const data = await response.json();
      if (!response.ok) {
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

  const handleRegister = async () => {
    if (!email || !password || !fullName) {
      notify('Please fill all fields', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, full_name: fullName, password }),
    });
    if (result.ok) {
      notify('Registration successful! Please login.');
      setAuthTab('login');
      setEmail('');
      setPassword('');
      setFullName('');
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
      setToken(result.data.access_token);
      setUserRole(parseRoleFromToken(result.data.access_token));
      notify('Logged in successfully!');
      setEmail('');
      setPassword('');
    }
  };

  const handleCreatePatrol = async () => {
    if (!patrolForm.name || !patrolForm.assigned_to) {
      notify('Please fill required fields', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/patrols/`, {
      method: 'POST',
      body: JSON.stringify(patrolForm),
    });
    if (result.ok) {
      notify('Patrol created successfully!');
      setPatrols([...patrols, result.data]);
      setPatrolForm({ name: '', description: '', assigned_to: '', start_time: '', end_time: '' });
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
    if (!patrolForm.name || !patrolForm.assigned_to) {
      notify('Please fill required fields', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/patrols/${editingPatrolId}`, {
      method: 'PUT',
      body: JSON.stringify(patrolForm),
    });
    if (result.ok) {
      notify('Patrol updated successfully!');
      setPatrols(patrols.map((p) => p.id === editingPatrolId ? result.data : p));
      setPatrolForm({ name: '', description: '', assigned_to: '', start_time: '', end_time: '' });
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
    }
  };

  const startEditPatrol = (patrol) => {
    setPatrolForm({
      name: patrol.name,
      description: patrol.description,
      assigned_to: patrol.assigned_to,
      start_time: patrol.start_time,
      end_time: patrol.end_time,
    });
    setEditingPatrolId(patrol.id);
    setShowEditPatrolModal(true);
  };

  const closeEditPatrol = () => {
    setShowEditPatrolModal(false);
    setEditingPatrolId(null);
  };

  const startEditOfficer = (officer) => {
    setOfficerForm({
      name: officer.name,
      badge: officer.badge,
      status: officer.status,
      zone: officer.zone,
    });
    setEditingOfficerId(officer.id);
    setShowEditOfficerModal(true);
  };

  const closeEditOfficer = () => {
    setShowEditOfficerModal(false);
    setEditingOfficerId(null);
    setOfficerForm({ name: '', badge: '', status: '', zone: '' });
  };

  const handleUpdateOfficer = () => {
    if (!officerForm.name || !officerForm.badge) {
      notify('Name and badge are required', 'error');
      return;
    }

    setOfficers(officers.map((o) => (
      o.id === editingOfficerId
        ? {
            ...o,
            name: officerForm.name,
            badge: officerForm.badge,
            status: officerForm.status || 'On Duty',
            zone: officerForm.zone,
          }
        : o
    )));
    notify('Officer updated successfully!');
    closeEditOfficer();
  };

  const requestRemoveOfficer = (officerId) => {
    setRemovingOfficerId(officerId);
    setShowRemoveOfficerModal(true);
  };

  const closeRemoveOfficer = () => {
    setShowRemoveOfficerModal(false);
    setRemovingOfficerId(null);
  };

  const confirmRemoveOfficer = () => {
    if (removingOfficerId === null) return;
    setOfficers(officers.filter((o) => o.id !== removingOfficerId));
    notify('Officer removed successfully!');
    closeRemoveOfficer();
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
      location: incident.location,
      severity: incident.severity,
      status: incident.status,
    });
    setEditingIncidentId(incident.id);
    setShowEditIncidentModal(true);
  };

  const closeEditIncident = () => {
    setShowEditIncidentModal(false);
    setEditingIncidentId(null);
    setIncidentForm({ title: '', location: '', severity: '', status: '' });
  };

  const handleUpdateIncident = () => {
    if (!incidentForm.title || !incidentForm.location) {
      notify('Title and location are required', 'error');
      return;
    }

    setIncidents(incidents.map((i) => (
      i.id === editingIncidentId
        ? {
            ...i,
            title: incidentForm.title,
            location: incidentForm.location,
            severity: incidentForm.severity || 'medium',
            status: incidentForm.status || 'open',
          }
        : i
    )));
    notify('Incident updated successfully!');
    closeEditIncident();
  };

  const requestRemoveIncident = (incidentId) => {
    setRemovingIncidentId(incidentId);
    setShowRemoveIncidentModal(true);
  };

  const closeRemoveIncident = () => {
    setShowRemoveIncidentModal(false);
    setRemovingIncidentId(null);
  };

  const confirmRemoveIncident = () => {
    if (removingIncidentId === null) return;
    setIncidents(incidents.filter((i) => i.id !== removingIncidentId));
    notify('Incident removed successfully!');
    closeRemoveIncident();
  };

  const startEditCheckpoint = (checkpoint) => {
    setCheckpointForm({
      name: checkpoint.name,
      zone: checkpoint.zone,
      status: checkpoint.status,
      lastCheck: toDateTimeLocal(checkpoint.lastCheck),
    });
    setEditingCheckpointId(checkpoint.id);
    setShowEditCheckpointModal(true);
  };

  const closeEditCheckpoint = () => {
    setShowEditCheckpointModal(false);
    setEditingCheckpointId(null);
    setCheckpointForm({ name: '', zone: '', status: '', lastCheck: '' });
  };

  const handleUpdateCheckpoint = () => {
    if (!checkpointForm.name || !checkpointForm.zone) {
      notify('Name and zone are required', 'error');
      return;
    }

    setCheckpoints(checkpoints.map((c) => (
      c.id === editingCheckpointId
        ? {
            ...c,
            name: checkpointForm.name,
            zone: checkpointForm.zone,
            status: checkpointForm.status || 'active',
            lastCheck: checkpointForm.lastCheck ? new Date(checkpointForm.lastCheck) : c.lastCheck,
          }
        : c
    )));
    notify('Checkpoint updated successfully!');
    closeEditCheckpoint();
  };

  const requestRemoveCheckpoint = (checkpointId) => {
    setRemovingCheckpointId(checkpointId);
    setShowRemoveCheckpointModal(true);
  };

  const closeRemoveCheckpoint = () => {
    setShowRemoveCheckpointModal(false);
    setRemovingCheckpointId(null);
  };

  const confirmRemoveCheckpoint = () => {
    if (removingCheckpointId === null) return;
    setCheckpoints(checkpoints.filter((c) => c.id !== removingCheckpointId));
    notify('Checkpoint removed successfully!');
    closeRemoveCheckpoint();
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

  const loadCommunications = async () => {
    const result = await apiCall(`${API_BASE}/alerts/`, { method: 'GET' });
    if (result.ok) {
      setCommunications(result.data);
    }
  };

  const handleCreateCommunication = async () => {
    if (!communicationForm.title || !communicationForm.severity) {
      notify('Title and severity are required', 'error');
      return;
    }
    const payload = {
      ...communicationForm,
      reported_at: new Date().toISOString(),
      patrol_id: null,
      device_id: null,
      customer_id: null,
    };
    const result = await apiCall(`${API_BASE}/alerts/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (result.ok) {
      setCommunications([result.data, ...communications]);
      setCommunicationForm({ title: '', description: '', severity: 'medium', status: 'open' });
      setShowCommunicationModal(false);
      notify('Communication logged successfully!');
    }
  };

  const startEditCommunication = (communication) => {
    setCommunicationForm({
      title: communication.title,
      description: communication.description || '',
      severity: communication.severity,
      status: communication.status,
    });
    setEditingCommunicationId(communication.id);
    setShowEditCommunicationModal(true);
  };

  const closeEditCommunication = () => {
    setShowEditCommunicationModal(false);
    setEditingCommunicationId(null);
    setCommunicationForm({ title: '', description: '', severity: 'medium', status: 'open' });
  };

  const handleUpdateCommunication = async () => {
    if (!communicationForm.title || !communicationForm.severity) {
      notify('Title and severity are required', 'error');
      return;
    }
    const existing = communications.find((c) => c.id === editingCommunicationId);
    const payload = {
      ...communicationForm,
      reported_at: existing?.reported_at || new Date().toISOString(),
      patrol_id: existing?.patrol_id ?? null,
      device_id: existing?.device_id ?? null,
      customer_id: existing?.customer_id ?? null,
    };
    const result = await apiCall(`${API_BASE}/alerts/${editingCommunicationId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    if (result.ok) {
      setCommunications(communications.map((c) => (c.id === editingCommunicationId ? result.data : c)));
      notify('Communication updated successfully!');
      closeEditCommunication();
    }
  };

  const requestRemoveCommunication = (communicationId) => {
    setRemovingCommunicationId(communicationId);
    setShowRemoveCommunicationModal(true);
  };

  const closeRemoveCommunication = () => {
    setShowRemoveCommunicationModal(false);
    setRemovingCommunicationId(null);
  };

  const confirmRemoveCommunication = async () => {
    if (removingCommunicationId === null) return;
    const result = await apiCall(`${API_BASE}/alerts/${removingCommunicationId}`, { method: 'DELETE' });
    if (result.ok) {
      setCommunications(communications.filter((c) => c.id !== removingCommunicationId));
      notify('Communication removed successfully!');
      closeRemoveCommunication();
    }
  };

  const loadDocuments = async () => {
    const result = await apiCall(`${API_BASE}/customers/`, { method: 'GET' });
    if (result.ok) {
      setDocuments(result.data);
    }
  };

  const handleCreateDocument = async () => {
    if (!documentForm.name) {
      notify('Site name is required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/customers/`, {
      method: 'POST',
      body: JSON.stringify(documentForm),
    });
    if (result.ok) {
      setDocuments([...documents, result.data]);
      setDocumentForm({ name: '', contact_email: '', phone: '', address: '' });
      setShowDocumentModal(false);
      notify('Site document created successfully!');
    }
  };

  const startEditDocument = (document) => {
    setDocumentForm({
      name: document.name,
      contact_email: document.contact_email || '',
      phone: document.phone || '',
      address: document.address || '',
    });
    setEditingDocumentId(document.id);
    setShowEditDocumentModal(true);
  };

  const closeEditDocument = () => {
    setShowEditDocumentModal(false);
    setEditingDocumentId(null);
    setDocumentForm({ name: '', contact_email: '', phone: '', address: '' });
  };

  const handleUpdateDocument = async () => {
    if (!documentForm.name) {
      notify('Site name is required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/customers/${editingDocumentId}`, {
      method: 'PUT',
      body: JSON.stringify(documentForm),
    });
    if (result.ok) {
      setDocuments(documents.map((d) => (d.id === editingDocumentId ? result.data : d)));
      notify('Site document updated successfully!');
      closeEditDocument();
    }
  };

  const requestRemoveDocument = (documentId) => {
    setRemovingDocumentId(documentId);
    setShowRemoveDocumentModal(true);
  };

  const closeRemoveDocument = () => {
    setShowRemoveDocumentModal(false);
    setRemovingDocumentId(null);
  };

  const confirmRemoveDocument = async () => {
    if (removingDocumentId === null) return;
    const result = await apiCall(`${API_BASE}/customers/${removingDocumentId}`, { method: 'DELETE' });
    if (result.ok) {
      setDocuments(documents.filter((d) => d.id !== removingDocumentId));
      notify('Site document removed successfully!');
      closeRemoveDocument();
    }
  };

  const handleInviteUser = async () => {
    if (!userForm.email || !userForm.password) {
      notify('Email and password are required', 'error');
      return;
    }
    const result = await apiCall(`${API_BASE}/users/`, {
      method: 'POST',
      body: JSON.stringify(userForm),
    });
    if (result.ok) {
      setManagedUsers([...managedUsers, result.data]);
      setUserForm({ email: '', full_name: '', password: '' });
      setShowUserModal(false);
      notify('User invited successfully!');
    }
  };

  const generateReport = () => {
    const report = {
      id: Date.now(),
      title: `Operational Snapshot ${new Date().toLocaleDateString()}`,
      range: 'Today',
      generated_at: new Date(),
      status: 'ready',
    };
    setReports([report, ...reports]);
    notify('Report generated successfully!');
  };

  const saveSettings = () => {
    notify('Settings saved successfully!');
  };

  useEffect(() => {
    if (!token) return;
    loadPatrols();
    loadVehicles();
    loadCommunications();
    loadDocuments();
  }, [token]);

  // Navigation items
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'dashboard', minRole: 'officer' },
    { id: 'patrols', label: 'Patrols', icon: 'patrols', minRole: 'officer' },
    { id: 'officers', label: 'Officers', icon: 'officers', minRole: 'supervisor' },
    { id: 'incidents', label: 'Incidents', icon: 'incidents', minRole: 'officer' },
    { id: 'checkpoints', label: 'Checkpoints', icon: 'checkpoints', minRole: 'officer' },
    { id: 'reports', label: 'Reports', icon: 'reports', minRole: 'supervisor' },
    { id: 'analytics', label: 'Analytics', icon: 'analytics', minRole: 'supervisor' },
    { id: 'vehicles', label: 'Vehicles', icon: 'vehicles', minRole: 'supervisor' },
    { id: 'communications', label: 'Communications', icon: 'communications', minRole: 'officer' },
    { id: 'documents', label: 'Documents', icon: 'documents', minRole: 'supervisor' },
    { id: 'users', label: 'Users', icon: 'users', minRole: 'admin' },
    { id: 'settings', label: 'Settings', icon: 'settings', minRole: 'admin' },
  ];

  const roleLevels = { officer: 1, supervisor: 2, admin: 3 };
  const visibleNavItems = navItems.filter((item) => roleLevels[userRole] >= roleLevels[item.minRole]);

  useEffect(() => {
    if (!token) return;
    const activeExists = visibleNavItems.some((item) => item.id === activeNav);
    if (!activeExists && visibleNavItems.length > 0) {
      setActiveNav(visibleNavItems[0].id);
    }
  }, [token, userRole, activeNav]);

  // Sidebar
  const Sidebar = () => {
    const { colors } = useTheme();
    return (
    <div style={{
      width: sidebarOpen ? 280 : 80,
      background: colors.sidebarBg,
      color: colors.sidebarText,
      padding: spacing.lg,
      display: 'flex',
      flexDirection: 'column',
      transition: transitions.base,
      borderRight: `1px solid ${colors.border}`,
      height: '100vh',
      overflowY: 'auto',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing.lg }}>
        {sidebarOpen && <h1 style={{ ...typography.headingMd, margin: 0, fontSize: 20, color: colors.sidebarText }}>PatrolPro</h1>}
        <button onClick={() => setSidebarOpen(!sidebarOpen)} style={{ background: 'transparent', border: 'none', color: colors.sidebarText, cursor: 'pointer', fontSize: 20 }}>
          <Icon name='menu' size={20} color={colors.sidebarText} />
        </button>
      </div>
      <nav style={{ flex: 1 }}>
        {visibleNavItems.map((item) => (
          <button
            key={item.id}
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
        {token && (
          <button onClick={() => { setToken(''); setUserRole('officer'); notify('Logged out'); }} style={{
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
    <div style={{
      background: colors.cardBg,
      borderBottom: `1px solid ${colors.border}`,
      padding: `${spacing.md} ${spacing.lg}`,
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: spacing.lg,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md, flex: 1 }}>
        <input
          type='text'
          placeholder='Search patrols, incidents, officers...'
          style={{
            padding: spacing.md, border: `1px solid ${colors.border}`,
            borderRadius: radius.md, width: '100%', maxWidth: 400,
            ...typography.bodyMd, background: colors.pageBg, color: colors.slate900,
          }}
        />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
        <button
          onClick={toggleDark}
          title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          style={{ background: colors.lightGrey, border: `1px solid ${colors.border}`, borderRadius: radius.md, padding: `${spacing.xs} ${spacing.sm}`, cursor: 'pointer', fontSize: 18 }}
        >
          {darkMode ? '☀️' : '🌙'}
        </button>
        <button style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', opacity: 0.7 }}>
          <Icon name='bell' size={20} />
        </button>
        {token ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
            <div style={{ width: 40, height: 40, borderRadius: '50%', background: colors.rosePink, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>
              {email.charAt(0).toUpperCase()}
            </div>
            <div>
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 600, color: colors.slate900 }}>{email.split('@')[0]}</p>
              <p style={{ ...typography.bodySm, margin: 0, color: colors.slate500, textTransform: 'capitalize' }}>{userRole}</p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
    );
  };

  // Dashboard Content
  const DashboardContent = () => {
    const { colors } = useTheme();
    return (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>Dashboard</h1>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Welcome back! Here's what's happening with your security operations today.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: spacing.lg, marginBottom: spacing.lg }}>
        <KPICard title="Active Patrols" value={String(patrols.length || 12)} subtitle="Live patrol routes" icon="patrols" trend={{ positive: true, percent: 33 }} />
        <KPICard title="Officers On Duty" value={String(officers.filter(o => o.status === 'On Duty').length)} subtitle="Currently active" icon="officers" trend={{ positive: true, percent: 12 }} />
        <KPICard title="Open Incidents" value={String(incidents.filter(i => i.status === 'open').length)} subtitle="Needs attention" icon="incidents" trend={{ positive: false, percent: 50 }} />
        <KPICard title="Active Checkpoints" value={String(checkpoints.filter(c => c.status === 'active').length)} subtitle="Perimeter secured" icon="checkpoints" trend={{ positive: true, percent: 8 }} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: spacing.lg, marginBottom: spacing.lg }}>
        <Card header="Active Patrols">
          <EnterpriseTable
            columns={[
              { key: 'officer', label: 'Officer' },
              { key: 'status', label: 'Status' },
              { key: 'route', label: 'Route' },
              { key: 'duration', label: 'Duration' },
            ]}
            rows={officers.map(o => ({ cells: { officer: o.name, status: o.status, route: o.zone, duration: '—' } }))}
            pageSize={5}
          />
        </Card>
        <Card header="Recent Incidents">
          <ActivityFeed items={incidents.slice(0, 4).map(i => ({
            icon: 'alertTriangle', title: i.title, description: i.location, time: i.status,
          }))} />
        </Card>
      </div>

      <Card header="Today's Schedule">
        <EnterpriseTable
          columns={[
            { key: 'time', label: 'Time' },
            { key: 'event', label: 'Event' },
            { key: 'officer', label: 'Officer' },
            { key: 'location', label: 'Location' },
          ]}
          rows={[
            { cells: { time: '08:00', event: 'Shift Start', officer: 'Team A', location: 'HQ' } },
            { cells: { time: '12:00', event: 'Lunch Break', officer: 'Half Team', location: 'Break Room' } },
            { cells: { time: '16:00', event: 'Evening Patrol', officer: 'Team B', location: 'All Zones' } },
          ]}
          pageSize={10}
        />
      </Card>
    </div>
    );
  };

  // Officers Content
  const OfficersContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Officers</h1>
          <Button icon="add">Add Officer</Button>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Manage your security officers and their assignments
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: spacing.lg,
      }}>
        {officers.map((officer) => (
          <Card key={officer.id} highlight>
            <h3 style={{ ...typography.headingSm, margin: 0, marginBottom: spacing.sm, color: colors.slate900 }}>
              {officer.name}
            </h3>
            <div style={{ marginBottom: spacing.md }}>
              <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Badge</p>
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 600, color: colors.slate900 }}>
                {officer.badge}
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
                <Badge variant={officer.status === 'On Duty' ? 'success' : 'warning'}>{officer.status}</Badge>
              </div>
              <div>
                <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Zone</p>
                <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 500 }}>{officer.zone}</p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: spacing.sm }}>
              <Button variant="secondary" size="sm" fullWidth icon="edit" onClick={() => startEditOfficer(officer)}>Edit</Button>
              <Button variant="danger" size="sm" fullWidth icon="trash" onClick={() => requestRemoveOfficer(officer.id)}>Remove</Button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={showEditOfficerModal} onClose={closeEditOfficer} title="Edit Officer">
        <TextField
          label="Name"
          value={officerForm.name}
          onChange={(v) => setOfficerForm({ ...officerForm, name: v })}
          placeholder="Officer name"
          autoFocus={true}
        />
        <TextField
          label="Badge"
          value={officerForm.badge}
          onChange={(v) => setOfficerForm({ ...officerForm, badge: v })}
          placeholder="P-001"
        />
        <TextField
          label="Status"
          value={officerForm.status}
          onChange={(v) => setOfficerForm({ ...officerForm, status: v })}
          placeholder="On Duty"
        />
        <TextField
          label="Zone"
          value={officerForm.zone}
          onChange={(v) => setOfficerForm({ ...officerForm, zone: v })}
          placeholder="Zone A"
        />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button onClick={closeEditOfficer} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={handleUpdateOfficer} fullWidth>Save Changes</Button>
        </div>
      </Modal>

      <Modal open={showRemoveOfficerModal} onClose={closeRemoveOfficer} title="Remove Officer">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>
          Are you sure you want to remove this officer?
        </p>
        <div style={{ display: 'flex', gap: spacing.md }}>
          <Button onClick={closeRemoveOfficer} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={confirmRemoveOfficer} variant="danger" fullWidth>Remove</Button>
        </div>
      </Modal>
    </div>
  );

  // Incidents Content
  const IncidentsContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Incidents</h1>
          <Button icon="add">Report Incident</Button>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Track and manage security incidents
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: spacing.lg,
      }}>
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
            <div style={{ display: 'flex', gap: spacing.sm }}>
              <Button variant="secondary" size="sm" fullWidth icon="edit" onClick={() => startEditIncident(incident)}>Edit</Button>
              <Button variant="danger" size="sm" fullWidth icon="trash" onClick={() => requestRemoveIncident(incident.id)}>Remove</Button>
            </div>
          </Card>
        ))}
      </div>

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
        <TextField
          label="Severity"
          value={incidentForm.severity}
          onChange={(v) => setIncidentForm({ ...incidentForm, severity: v })}
          placeholder="high | medium | low"
        />
        <TextField
          label="Status"
          value={incidentForm.status}
          onChange={(v) => setIncidentForm({ ...incidentForm, status: v })}
          placeholder="open | investigating | resolved"
        />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button onClick={closeEditIncident} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={handleUpdateIncident} fullWidth>Save Changes</Button>
        </div>
      </Modal>

      <Modal open={showRemoveIncidentModal} onClose={closeRemoveIncident} title="Remove Incident">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>
          Are you sure you want to remove this incident?
        </p>
        <div style={{ display: 'flex', gap: spacing.md }}>
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Checkpoints</h1>
          <Button icon="add">Add Checkpoint</Button>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Manage patrol checkpoints and verification points
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: spacing.lg,
      }}>
        {checkpoints.map((checkpoint) => (
          <Card key={checkpoint.id} highlight>
            <h3 style={{ ...typography.headingSm, margin: 0, marginBottom: spacing.sm, color: colors.slate900 }}>
              {checkpoint.name}
            </h3>
            <div style={{ marginBottom: spacing.md }}>
              <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Zone</p>
              <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 600, color: colors.slate900 }}>
                {checkpoint.zone}
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
                <Badge variant={checkpoint.status === 'active' ? 'success' : 'warning'}>{checkpoint.status}</Badge>
              </div>
              <div>
                <p style={{ ...typography.labelSm, color: colors.slate500, margin: 0 }}>Last Check</p>
                <p style={{ ...typography.bodyMd, margin: 0, fontWeight: 500 }}>
                  {new Date(checkpoint.lastCheck).toLocaleTimeString()}
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: spacing.sm }}>
              <Button variant="secondary" size="sm" fullWidth icon="edit" onClick={() => startEditCheckpoint(checkpoint)}>Edit</Button>
              <Button variant="danger" size="sm" fullWidth icon="trash" onClick={() => requestRemoveCheckpoint(checkpoint.id)}>Remove</Button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={showEditCheckpointModal} onClose={closeEditCheckpoint} title="Edit Checkpoint">
        <TextField
          label="Name"
          value={checkpointForm.name}
          onChange={(v) => setCheckpointForm({ ...checkpointForm, name: v })}
          placeholder="Checkpoint name"
          autoFocus={true}
        />
        <TextField
          label="Zone"
          value={checkpointForm.zone}
          onChange={(v) => setCheckpointForm({ ...checkpointForm, zone: v })}
          placeholder="Checkpoint zone"
        />
        <TextField
          label="Status"
          value={checkpointForm.status}
          onChange={(v) => setCheckpointForm({ ...checkpointForm, status: v })}
          placeholder="active | inactive"
        />
        <TextField
          label="Last Check"
          type="datetime-local"
          value={checkpointForm.lastCheck}
          onChange={(v) => setCheckpointForm({ ...checkpointForm, lastCheck: v })}
        />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button onClick={closeEditCheckpoint} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={handleUpdateCheckpoint} fullWidth>Save Changes</Button>
        </div>
      </Modal>

      <Modal open={showRemoveCheckpointModal} onClose={closeRemoveCheckpoint} title="Remove Checkpoint">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>
          Are you sure you want to remove this checkpoint?
        </p>
        <div style={{ display: 'flex', gap: spacing.md }}>
          <Button onClick={closeRemoveCheckpoint} variant="secondary" fullWidth>Cancel</Button>
          <Button onClick={confirmRemoveCheckpoint} variant="danger" fullWidth>Remove</Button>
        </div>
      </Modal>
    </div>
  );

  const ReportsContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Reports</h1>
          <Button icon="add" onClick={generateReport}>Generate Report</Button>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Build and review operational summaries for leadership and dispatch.
        </p>
      </div>

      <Card header="Report Library" actions={<Button variant="secondary" icon="load" onClick={() => notify('Report list is up to date')}>Refresh</Button>}>
        <EnterpriseTable
          columns={[
            { key: 'title', label: 'Title' },
            { key: 'range', label: 'Range' },
            { key: 'generated', label: 'Generated' },
            { key: 'status', label: 'Status' },
          ]}
          rows={reports.map((r) => ({
            cells: {
              title: r.title,
              range: r.range,
              generated: formatDateTime(r.generated_at),
              status: r.status,
            },
            id: r.id,
          }))}
          actions={(row) => (
            <>
              <Button size="sm" variant="secondary" icon="download" onClick={() => notify(`Downloading ${row.cells.title}`)}>Export</Button>
              <Button size="sm" variant="danger" icon="trash" onClick={() => setReports(reports.filter((r) => r.id !== row.id))}>Remove</Button>
            </>
          )}
        />
      </Card>
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

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: spacing.lg,
          marginBottom: spacing.lg,
        }}>
          <KPICard title="Open Incidents" value={String(openIncidents)} subtitle="Needs active follow-up" icon="incidents" color={colors.error} />
          <KPICard title="On-Duty Officers" value={String(onDutyOfficers)} subtitle="Currently active" icon="officers" color={colors.success} />
          <KPICard title="Active Checkpoints" value={String(activeCheckpoints)} subtitle="Perimeter verified" icon="checkpoints" color={colors.blushPink} />
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Vehicles</h1>
          <div style={{ display: 'flex', gap: spacing.md }}>
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
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={() => setShowVehicleModal(false)}>Cancel</Button>
          <Button fullWidth onClick={handleCreateVehicle}>Create</Button>
        </div>
      </Modal>

      <Modal open={showEditVehicleModal} onClose={closeEditVehicle} title="Edit Vehicle">
        <TextField label="Unit Name" value={vehicleForm.name} onChange={(v) => setVehicleForm({ ...vehicleForm, name: v })} placeholder="Patrol SUV 01" autoFocus={true} />
        <TextField label="Unit ID" value={vehicleForm.serial_number} onChange={(v) => setVehicleForm({ ...vehicleForm, serial_number: v })} placeholder="SUV-01" />
        <TextField label="Status" value={vehicleForm.status} onChange={(v) => setVehicleForm({ ...vehicleForm, status: v })} placeholder="active | maintenance" />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={closeEditVehicle}>Cancel</Button>
          <Button fullWidth onClick={handleUpdateVehicle}>Save</Button>
        </div>
      </Modal>

      <Modal open={showRemoveVehicleModal} onClose={closeRemoveVehicle} title="Remove Vehicle">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>Are you sure you want to remove this vehicle?</p>
        <div style={{ display: 'flex', gap: spacing.md }}>
          <Button variant="secondary" fullWidth onClick={closeRemoveVehicle}>Cancel</Button>
          <Button variant="danger" fullWidth onClick={confirmRemoveVehicle}>Remove</Button>
        </div>
      </Modal>
    </div>
  );

  const CommunicationsContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Communications</h1>
          <div style={{ display: 'flex', gap: spacing.md }}>
            <Button variant="secondary" icon="load" onClick={loadCommunications}>Refresh</Button>
            <Button icon="add" onClick={() => setShowCommunicationModal(true)}>Log Message</Button>
          </div>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Dispatch messages and urgent operations communication logs.
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: spacing.lg,
      }}>
        {communications.map((item) => (
          <Card key={item.id} highlight>
            <h3 style={{ ...typography.headingSm, margin: 0, marginBottom: spacing.sm, color: colors.slate900 }}>{item.title}</h3>
            <p style={{ ...typography.bodySm, margin: 0, marginBottom: spacing.md, color: colors.slate500 }}>{item.description || 'No additional details'}</p>
            <div style={{ display: 'flex', gap: spacing.sm, marginBottom: spacing.md }}>
              <Badge variant={item.severity === 'high' ? 'error' : item.severity === 'medium' ? 'warning' : 'info'}>{item.severity}</Badge>
              <Badge variant={item.status === 'open' ? 'error' : item.status === 'investigating' ? 'warning' : 'success'}>{item.status}</Badge>
            </div>
            <p style={{ ...typography.labelSm, color: colors.slate500, marginBottom: spacing.md }}>
              Reported: {formatDateTime(item.reported_at)}
            </p>
            <div style={{ display: 'flex', gap: spacing.sm }}>
              <Button size="sm" variant="secondary" fullWidth icon="edit" onClick={() => startEditCommunication(item)}>Edit</Button>
              <Button size="sm" variant="danger" fullWidth icon="trash" onClick={() => requestRemoveCommunication(item.id)}>Remove</Button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={showCommunicationModal} onClose={() => setShowCommunicationModal(false)} title="New Communication">
        <TextField label="Title" value={communicationForm.title} onChange={(v) => setCommunicationForm({ ...communicationForm, title: v })} placeholder="Dispatch message title" autoFocus={true} />
        <TextField label="Description" value={communicationForm.description} onChange={(v) => setCommunicationForm({ ...communicationForm, description: v })} placeholder="Message details" />
        <TextField label="Severity" value={communicationForm.severity} onChange={(v) => setCommunicationForm({ ...communicationForm, severity: v })} placeholder="high | medium | low" />
        <TextField label="Status" value={communicationForm.status} onChange={(v) => setCommunicationForm({ ...communicationForm, status: v })} placeholder="open | investigating | resolved" />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={() => setShowCommunicationModal(false)}>Cancel</Button>
          <Button fullWidth onClick={handleCreateCommunication}>Create</Button>
        </div>
      </Modal>

      <Modal open={showEditCommunicationModal} onClose={closeEditCommunication} title="Edit Communication">
        <TextField label="Title" value={communicationForm.title} onChange={(v) => setCommunicationForm({ ...communicationForm, title: v })} placeholder="Dispatch message title" autoFocus={true} />
        <TextField label="Description" value={communicationForm.description} onChange={(v) => setCommunicationForm({ ...communicationForm, description: v })} placeholder="Message details" />
        <TextField label="Severity" value={communicationForm.severity} onChange={(v) => setCommunicationForm({ ...communicationForm, severity: v })} placeholder="high | medium | low" />
        <TextField label="Status" value={communicationForm.status} onChange={(v) => setCommunicationForm({ ...communicationForm, status: v })} placeholder="open | investigating | resolved" />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={closeEditCommunication}>Cancel</Button>
          <Button fullWidth onClick={handleUpdateCommunication}>Save</Button>
        </div>
      </Modal>

      <Modal open={showRemoveCommunicationModal} onClose={closeRemoveCommunication} title="Remove Communication">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>Are you sure you want to remove this communication record?</p>
        <div style={{ display: 'flex', gap: spacing.md }}>
          <Button variant="secondary" fullWidth onClick={closeRemoveCommunication}>Cancel</Button>
          <Button variant="danger" fullWidth onClick={confirmRemoveCommunication}>Remove</Button>
        </div>
      </Modal>
    </div>
  );

  const DocumentsContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Documents</h1>
          <div style={{ display: 'flex', gap: spacing.md }}>
            <Button variant="secondary" icon="load" onClick={loadDocuments}>Refresh</Button>
            <Button icon="add" onClick={() => setShowDocumentModal(true)}>Add Site File</Button>
          </div>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Site records, contact sheets, and address profiles.
        </p>
      </div>

      <Card header="Site Document Register">
        <EnterpriseTable
          columns={[
            { key: 'name', label: 'Site' },
            { key: 'email', label: 'Email' },
            { key: 'phone', label: 'Phone' },
            { key: 'address', label: 'Address' },
          ]}
          rows={documents.map((d) => ({
            cells: { name: d.name, email: d.contact_email || 'Not set', phone: d.phone || 'Not set', address: d.address || 'Not set' },
            id: d.id, raw: d,
          }))}
          actions={(row) => (
            <>
              <Button size="sm" variant="secondary" icon="edit" onClick={() => startEditDocument(row.raw)}>Edit</Button>
              <Button size="sm" variant="danger" icon="trash" onClick={() => requestRemoveDocument(row.id)}>Remove</Button>
            </>
          )}
        />
      </Card>

      <Modal open={showDocumentModal} onClose={() => setShowDocumentModal(false)} title="Create Site Document">
        <TextField label="Site Name" value={documentForm.name} onChange={(v) => setDocumentForm({ ...documentForm, name: v })} placeholder="Warehouse C" autoFocus={true} />
        <TextField label="Contact Email" value={documentForm.contact_email} onChange={(v) => setDocumentForm({ ...documentForm, contact_email: v })} placeholder="ops@example.com" />
        <TextField label="Phone" value={documentForm.phone} onChange={(v) => setDocumentForm({ ...documentForm, phone: v })} placeholder="555-1000" />
        <TextField label="Address" value={documentForm.address} onChange={(v) => setDocumentForm({ ...documentForm, address: v })} placeholder="100 Main St" />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={() => setShowDocumentModal(false)}>Cancel</Button>
          <Button fullWidth onClick={handleCreateDocument}>Create</Button>
        </div>
      </Modal>

      <Modal open={showEditDocumentModal} onClose={closeEditDocument} title="Edit Site Document">
        <TextField label="Site Name" value={documentForm.name} onChange={(v) => setDocumentForm({ ...documentForm, name: v })} placeholder="Warehouse C" autoFocus={true} />
        <TextField label="Contact Email" value={documentForm.contact_email} onChange={(v) => setDocumentForm({ ...documentForm, contact_email: v })} placeholder="ops@example.com" />
        <TextField label="Phone" value={documentForm.phone} onChange={(v) => setDocumentForm({ ...documentForm, phone: v })} placeholder="555-1000" />
        <TextField label="Address" value={documentForm.address} onChange={(v) => setDocumentForm({ ...documentForm, address: v })} placeholder="100 Main St" />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={closeEditDocument}>Cancel</Button>
          <Button fullWidth onClick={handleUpdateDocument}>Save</Button>
        </div>
      </Modal>

      <Modal open={showRemoveDocumentModal} onClose={closeRemoveDocument} title="Remove Site Document">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>Are you sure you want to remove this site document?</p>
        <div style={{ display: 'flex', gap: spacing.md }}>
          <Button variant="secondary" fullWidth onClick={closeRemoveDocument}>Cancel</Button>
          <Button variant="danger" fullWidth onClick={confirmRemoveDocument}>Remove</Button>
        </div>
      </Modal>
    </div>
  );

  const UsersContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md }}>
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>Users</h1>
          <Button icon="add" onClick={() => setShowUserModal(true)}>Invite User</Button>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Create additional platform users for your operations team.
        </p>
      </div>

      <Card header="Recently Invited Users">
        {managedUsers.length === 0 ? (
          <p style={{ ...typography.bodyMd, color: colors.slate500 }}>No invited users yet.</p>
        ) : (
          <EnterpriseTable
            columns={[
              { key: 'email', label: 'Email' },
              { key: 'name', label: 'Name' },
              { key: 'id', label: 'User ID' },
            ]}
            rows={managedUsers.map((u) => ({
              cells: { email: u.email, name: u.full_name || 'Not set', id: String(u.id) },
            }))}
          />
        )}
      </Card>

      <Modal open={showUserModal} onClose={() => setShowUserModal(false)} title="Invite User">
        <TextField label="Full Name" value={userForm.full_name} onChange={(v) => setUserForm({ ...userForm, full_name: v })} placeholder="Alex Morgan" autoFocus={true} />
        <TextField label="Email" value={userForm.email} onChange={(v) => setUserForm({ ...userForm, email: v })} placeholder="alex@patrolpro.com" />
        <TextField label="Temporary Password" type="password" value={userForm.password} onChange={(v) => setUserForm({ ...userForm, password: v })} placeholder="Temporary password" />
        <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={() => setShowUserModal(false)}>Cancel</Button>
          <Button fullWidth onClick={handleInviteUser}>Invite</Button>
        </div>
      </Modal>
    </div>
  );

  const SettingsContent = () => (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <h1 style={{ ...typography.headingXL, margin: 0, marginBottom: spacing.md, color: colors.slate900 }}>Settings</h1>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Configure global defaults for operations and notifications.
        </p>
      </div>

      <Card header="Organization Settings">
        <TextField label="Company Name" value={settingsForm.companyName} onChange={(v) => setSettingsForm({ ...settingsForm, companyName: v })} />
        <TextField label="Default Shift Length (hours)" value={settingsForm.defaultShiftLength} onChange={(v) => setSettingsForm({ ...settingsForm, defaultShiftLength: v })} />
        <TextField label="Incident Escalation (minutes)" value={settingsForm.incidentEscalationMinutes} onChange={(v) => setSettingsForm({ ...settingsForm, incidentEscalationMinutes: v })} />
        <TextField label="Email Notifications" value={settingsForm.emailNotifications} onChange={(v) => setSettingsForm({ ...settingsForm, emailNotifications: v })} placeholder="enabled | disabled" />
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={saveSettings}>Save Settings</Button>
        </div>
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
        handleLogin={handleLogin} 
        handleRegister={handleRegister}
      />
    );

    switch (activeNav) {
      case 'dashboard':
        return <DashboardContent />;
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
          />
        );
      case 'officers':
        return <OfficersContent />;
      case 'incidents':
        return <IncidentsContent />;
      case 'checkpoints':
        return <CheckpointsContent />;
      case 'reports':
        return <ReportsContent />;
      case 'analytics':
        return <AnalyticsContent />;
      case 'vehicles':
        return <VehiclesContent />;
      case 'communications':
        return <CommunicationsContent />;
      case 'documents':
        return <DocumentsContent />;
      case 'users':
        return <UsersContent />;
      case 'settings':
        return <SettingsContent />;
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
    <div style={{
      display: 'flex',
      height: '100vh',
      background: colors.pageBg,
      fontFamily: '"Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", sans-serif',
      color: colors.slate900,
    }}>
      {token && <Sidebar />}

      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {token && <TopNav darkMode={dark} toggleDark={toggle} />}

        <main style={{
          flex: 1,
          overflow: 'auto',
          padding: spacing.lg,
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
