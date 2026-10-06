import { ViewStyle } from 'react-native';

import { colors } from './colors';

/**
 * Soft card shadow. Source of truth: design/DESIGN.md
 */
export const shadows: Record<'card' | 'button', ViewStyle> = {
  card: {
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 2,
  },
  button: {
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 10,
    elevation: 2,
  },
};
