import { useEffect, useState } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';

import { Caption } from '@/components/ui/TextBlock';
import { colors, radius, spacing } from '@/theme';

interface RecordingIndicatorProps {
  active: boolean;
  label?: string;
}

const BAR_COUNT = 5;

/**
 * Animated bar meter shown while a mock recording is in progress.
 */
export function RecordingIndicator({ active, label }: RecordingIndicatorProps) {
  // Held in state, not a ref, because the animated value is read during render.
  const [progress] = useState(() => new Animated.Value(0));

  useEffect(() => {
    if (!active) {
      progress.setValue(0);
      return;
    }

    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(progress, {
          toValue: 1,
          duration: 700,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: false,
        }),
        Animated.timing(progress, {
          toValue: 0,
          duration: 700,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: false,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [active, progress]);

  const heightFor = (index: number) => {
    const base = 10 + index * 4;
    return progress.interpolate({
      inputRange: [0, 1],
      outputRange: [base, base + 22],
    });
  };

  return (
    <View style={styles.wrapper}>
      <View
        style={styles.bars}
        accessibilityRole="progressbar"
        accessibilityLabel={active ? 'Recording in progress' : 'Not recording'}>
        {Array.from({ length: BAR_COUNT }).map((_, index) => (
          <Animated.View
            key={index}
            style={[
              styles.bar,
              {
                height: active ? heightFor(index) : 12,
                backgroundColor: active ? colors.danger : colors.disabled,
              },
            ]}
          />
        ))}
      </View>
      <Caption>{label ?? (active ? 'Listening…' : 'Ready when you are')}</Caption>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    gap: spacing.sm,
  },
  bars: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.xs,
    height: 44,
  },
  bar: {
    width: 8,
    borderRadius: radius.pill,
  },
});
