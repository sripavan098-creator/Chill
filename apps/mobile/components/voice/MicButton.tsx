import { Pressable, StyleSheet, View } from 'react-native';

import { Body } from '@/components/ui/TextBlock';
import { colors, radius, shadows, spacing } from '@/theme';

interface MicButtonProps {
  onPress: () => void;
  active?: boolean;
  disabled?: boolean;
  size?: number;
  caption?: string;
  accessibilityLabel?: string;
  testID?: string;
}

/**
 * Large circular microphone button. Drawn with plain views so no icon
 * dependency is required in v0.1.
 */
export function MicButton({
  onPress,
  active = false,
  disabled = false,
  size = 148,
  caption,
  accessibilityLabel = 'Record voice',
  testID,
}: MicButtonProps) {
  const diameter = size;
  const inner = size * 0.62;

  return (
    <View style={styles.wrapper}>
      <Pressable
        testID={testID}
        onPress={onPress}
        disabled={disabled}
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel}
        accessibilityState={{ disabled, busy: active }}
        style={({ pressed }) => [
          styles.button,
          {
            width: diameter,
            height: diameter,
            borderRadius: radius.circle,
            backgroundColor: active ? colors.primaryDark : colors.primary,
            opacity: disabled ? 0.45 : pressed ? 0.9 : 1,
          },
          !disabled ? shadows.button : null,
        ]}>
        <View
          style={[
            styles.inner,
            {
              width: inner,
              height: inner,
              borderRadius: radius.circle,
              backgroundColor: active ? colors.danger : colors.card,
            },
          ]}
        />
      </Pressable>
      {caption ? (
        <Body color={colors.textSecondary} center>
          {caption}
        </Body>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    gap: spacing.md,
  },
  button: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  inner: {
    opacity: 0.92,
  },
});
