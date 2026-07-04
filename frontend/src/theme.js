// Professional Light Pink Theme & Design System
// Supports light and dark modes via CSS custom properties

export const lightTokens = {
  // Brand
  blushPink: '#F8B4C8',
  rosePink: '#F472B6',
  softLavender: '#E9D5FF',
  dustyMauve: '#D8B4FE',

  // Surfaces
  white: '#FFFFFF',
  softPink: '#FFF5F8',
  lightGrey: '#F8FAFC',
  pageBg: '#F8FAFC',
  cardBg: '#FFFFFF',
  sidebarBg: '#0F172A',
  sidebarText: '#FFFFFF',

  // Text
  slate900: '#0F172A',
  slate700: '#334155',
  slate500: '#64748B',
  slate400: '#94A3B8',
  slate300: '#CBD5E1',
  slate200: '#E2E8F0',
  slate100: '#F1F5F9',

  // Status
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',

  // Semantic
  border: '#E2E8F0',
  shadow: 'rgba(15, 23, 42, 0.08)',
  shadowHover: 'rgba(15, 23, 42, 0.12)',
  skeletonBase: '#E2E8F0',
  skeletonHighlight: '#F1F5F9',
};

export const darkTokens = {
  blushPink: '#F8B4C8',
  rosePink: '#F472B6',
  softLavender: '#6D28D9',
  dustyMauve: '#7C3AED',

  white: '#1E293B',
  softPink: '#1E2433',
  lightGrey: '#0F172A',
  pageBg: '#0F172A',
  cardBg: '#1E293B',
  sidebarBg: '#020617',
  sidebarText: '#E2E8F0',

  slate900: '#F1F5F9',
  slate700: '#CBD5E1',
  slate500: '#94A3B8',
  slate400: '#64748B',
  slate300: '#334155',
  slate200: '#1E293B',
  slate100: '#0F172A',

  success: '#4ADE80',
  warning: '#FCD34D',
  error: '#F87171',
  info: '#60A5FA',

  border: '#334155',
  shadow: 'rgba(0, 0, 0, 0.4)',
  shadowHover: 'rgba(0, 0, 0, 0.6)',
  skeletonBase: '#334155',
  skeletonHighlight: '#475569',
};

export const colors = lightTokens;

// Spacing System (8px base)
export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
};

// Border Radius
export const radius = {
  sm: '6px',
  md: '12px',
  lg: '16px',
};

// Typography
export const typography = {
  headingXL: { fontSize: '32px', fontWeight: 700, lineHeight: '40px' },
  headingLg: { fontSize: '28px', fontWeight: 700, lineHeight: '36px' },
  headingMd: { fontSize: '24px', fontWeight: 700, lineHeight: '32px' },
  headingSm: { fontSize: '18px', fontWeight: 600, lineHeight: '26px' },
  headingXs: { fontSize: '16px', fontWeight: 600, lineHeight: '24px' },
  bodyLg: { fontSize: '16px', fontWeight: 400, lineHeight: '24px' },
  bodyMd: { fontSize: '14px', fontWeight: 400, lineHeight: '20px' },
  bodySm: { fontSize: '13px', fontWeight: 400, lineHeight: '18px' },
  labelMd: { fontSize: '13px', fontWeight: 600, lineHeight: '18px' },
  labelSm: { fontSize: '12px', fontWeight: 600, lineHeight: '16px' },
};

// Shadow System
export const shadows = {
  none: 'none',
  xs: `0 1px 2px ${colors.shadow}`,
  sm: `0 1px 3px ${colors.shadow}, 0 1px 2px rgba(15, 23, 42, 0.06)`,
  md: `0 4px 6px ${colors.shadow}, 0 2px 4px rgba(15, 23, 42, 0.06)`,
  lg: `0 10px 15px ${colors.shadowHover}, 0 4px 6px rgba(15, 23, 42, 0.05)`,
  xl: `0 20px 25px ${colors.shadowHover}, 0 10px 10px rgba(15, 23, 42, 0.04)`,
};

// Transitions
export const transitions = {
  fast: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
  base: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
  slow: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
};

// Z-Index
export const zIndex = {
  hide: -1,
  auto: 'auto',
  base: 0,
  dropdown: 1000,
  sticky: 1020,
  fixed: 1030,
  modalBackdrop: 1040,
  modal: 1050,
  popover: 1060,
  tooltip: 1070,
};
