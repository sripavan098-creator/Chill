/**
 * Chill color tokens.
 * Source of truth: design/DESIGN.md
 */
export const colors = {
  primary: '#0D9488',
  primaryDark: '#0F766E',
  primarySoft: '#CCFBF1',
  background: '#F8FAFC',
  card: '#FFFFFF',
  textPrimary: '#0F172A',
  textSecondary: '#64748B',
  textOnPrimary: '#FFFFFF',
  success: '#22C55E',
  successSoft: '#DCFCE7',
  warning: '#F59E0B',
  warningSoft: '#FEF3C7',
  danger: '#EF4444',
  dangerSoft: '#FEE2E2',
  border: '#E2E8F0',
  overlay: 'rgba(15, 23, 42, 0.45)',
  disabled: '#CBD5E1',
} as const;

export type ColorToken = keyof typeof colors;
