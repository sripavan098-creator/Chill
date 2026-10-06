/**
 * Chill spacing scale. Source of truth: design/DESIGN.md (4px base).
 */
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radius = {
  button: 16,
  card: 20,
  input: 14,
  pill: 999,
  circle: 999,
} as const;

export type SpacingToken = keyof typeof spacing;
export type RadiusToken = keyof typeof radius;
