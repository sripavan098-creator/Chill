import { colors } from './colors';
import { shadows } from './shadows';
import { radius, spacing } from './spacing';
import { typography } from './typography';

export { colors } from './colors';
export type { ColorToken } from './colors';
export { radius, spacing } from './spacing';
export type { RadiusToken, SpacingToken } from './spacing';
export { typography } from './typography';
export type { TypographyToken } from './typography';
export { shadows } from './shadows';

export const theme = {
  colors,
  spacing,
  radius,
  typography,
  shadows,
} as const;
