import { StyleSheet, View } from 'react-native';

import { Caption } from '@/components/ui/TextBlock';
import { colors, radius, spacing } from '@/theme';

interface RecordingTimerProps {
  elapsedMs: number;
  maxMs: number;
  active: boolean;
}

/**
 * Visible recording timer with a fill bar so the speaker can see how much
 * time is left before the automatic stop.
 */
export function RecordingTimer({ elapsedMs, maxMs, active }: RecordingTimerProps) {
  const ratio = maxMs === 0 ? 0 : Math.min(elapsedMs / maxMs, 1);
  const seconds = (elapsedMs / 1000).toFixed(1);
  const limit = (maxMs / 1000).toFixed(0);

  return (
    <View style={styles.wrapper}>
      <View style={styles.track}>
        <View
          style={[styles.fill, { width: `${ratio * 100}%` }]}
          accessibilityRole="progressbar"
          accessibilityLabel="Recording timer"
          accessibilityValue={{ min: 0, max: maxMs, now: Math.round(elapsedMs) }}
        />
      </View>
      <Caption color={active ? colors.danger : colors.textSecondary}>
        {`${seconds}s of ${limit}s`}
      </Caption>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: spacing.xs,
  },
  track: {
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.border,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: radius.pill,
    backgroundColor: colors.danger,
  },
});
