import { StyleSheet, View } from 'react-native';

import { Body, Caption } from '@/components/ui/TextBlock';
import { colors, radius, spacing } from '@/theme';

type Tone = 'info' | 'success' | 'warning' | 'danger';

interface BadgeProps {
  label: string;
  tone?: Tone;
}

const TONE: Record<Tone, { background: string; text: string }> = {
  info: { background: colors.primarySoft, text: colors.primaryDark },
  success: { background: colors.successSoft, text: colors.success },
  warning: { background: colors.warningSoft, text: colors.warning },
  danger: { background: colors.dangerSoft, text: colors.danger },
};

export function Badge({ label, tone = 'info' }: BadgeProps) {
  const palette = TONE[tone];
  return (
    <View style={[styles.badge, { backgroundColor: palette.background }]}>
      <Caption style={[styles.label, { color: palette.text }]}>{label}</Caption>
    </View>
  );
}

interface InfoRowProps {
  label: string;
  value: string;
  tone?: 'default' | 'success' | 'danger';
}

const VALUE_COLOR = {
  default: colors.textPrimary,
  success: colors.success,
  danger: colors.danger,
};

export function InfoRow({ label, value, tone = 'default' }: InfoRowProps) {
  return (
    <View style={styles.row}>
      <Body color={colors.textSecondary}>{label}</Body>
      <Body color={VALUE_COLOR[tone]}>{value}</Body>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: radius.pill,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
  },
  label: {
    fontWeight: '600',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
  },
});
