import { PropsWithChildren } from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';

import { colors, radius, shadows, spacing } from '@/theme';

interface CardProps {
  style?: ViewStyle;
  /** Soft teal tint, used for highlighted or empty states. */
  tone?: 'default' | 'muted' | 'success' | 'danger';
  testID?: string;
}

const TONE_BACKGROUND: Record<NonNullable<CardProps['tone']>, string> = {
  default: colors.card,
  muted: colors.primarySoft,
  success: colors.successSoft,
  danger: colors.dangerSoft,
};

export function Card({
  children,
  style,
  tone = 'default',
  testID,
}: PropsWithChildren<CardProps>) {
  return (
    <View
      testID={testID}
      style={[
        styles.card,
        { backgroundColor: TONE_BACKGROUND[tone] },
        style,
      ]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radius.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.md,
    ...shadows.card,
  },
});
