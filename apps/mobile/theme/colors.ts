/**
 * Chill color tokens: warm paper, ink, one voice color.
 * Source of truth: design/DESIGN.md
 */
export const colors = {
  primary: '#C94A16',
  primaryDark: '#A93C0F',
  primarySoft: '#FBE4D8',
  voice: '#E8602C',
  calm: '#4F8A76',
  cool: '#9A9186',
  background: '#F6F0E6',
  card: '#FFFAF1',
  textPrimary: '#241D17',
  textSecondary: '#6F6458',
  textOnPrimary: '#FFFFFF',
  success: '#3F7A66',
  successSoft: '#DDEBE4',
  warning: '#9A6410',
  warningSoft: '#F7E8C8',
  danger: '#B3321F',
  dangerSoft: '#F6DAD4',
  border: '#E4D9C6',
  overlay: 'rgba(36, 29, 23, 0.45)',
  disabled: '#CFC4B2',
} as const;

export type ColorToken = keyof typeof colors;
