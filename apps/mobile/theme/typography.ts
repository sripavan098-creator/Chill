import { Platform, TextStyle } from 'react-native';

import { colors } from './colors';

const fontFamily = Platform.select({
  ios: 'system-ui',
  android: 'sans-serif',
  default: 'System',
});

/**
 * Chill typography scale. Source of truth: design/DESIGN.md
 */
export const typography = {
  title: {
    fontFamily,
    fontSize: 24,
    fontWeight: '600',
    lineHeight: 32,
    color: colors.textPrimary,
  } satisfies TextStyle,
  heading: {
    fontFamily,
    fontSize: 20,
    fontWeight: '600',
    lineHeight: 28,
    color: colors.textPrimary,
  } satisfies TextStyle,
  body: {
    fontFamily,
    fontSize: 16,
    fontWeight: '400',
    lineHeight: 24,
    color: colors.textPrimary,
  } satisfies TextStyle,
  bodyStrong: {
    fontFamily,
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 24,
    color: colors.textPrimary,
  } satisfies TextStyle,
  caption: {
    fontFamily,
    fontSize: 13,
    fontWeight: '400',
    lineHeight: 18,
    color: colors.textSecondary,
  } satisfies TextStyle,
  button: {
    fontFamily,
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 20,
  } satisfies TextStyle,
} as const;

export type TypographyToken = keyof typeof typography;
