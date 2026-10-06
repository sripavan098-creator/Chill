import { StyleSheet, View } from 'react-native';

import { Caption } from '@/components/ui/TextBlock';
import { colors, radius, spacing } from '@/theme';

interface EnrollmentProgressProps {
  completed: number;
  total: number;
}

export function EnrollmentProgress({ completed, total }: EnrollmentProgressProps) {
  const ratio = total === 0 ? 0 : Math.min(completed / total, 1);

  return (
    <View style={styles.wrapper}>
      <View style={styles.track}>
        <View
          style={[styles.fill, { width: `${ratio * 100}%` }]}
          accessibilityRole="progressbar"
          accessibilityLabel={`${completed} of ${total} phrases recorded`}
          accessibilityValue={{ min: 0, max: total, now: completed }}
        />
      </View>
      <Caption>{`${completed} of ${total} phrases captured`}</Caption>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: spacing.sm,
  },
  track: {
    height: 10,
    borderRadius: radius.pill,
    backgroundColor: colors.border,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: radius.pill,
    backgroundColor: colors.primary,
  },
});
