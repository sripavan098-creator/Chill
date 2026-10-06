import { Pressable, StyleSheet, View } from 'react-native';

import { Caption } from '@/components/ui/TextBlock';
import { colors, radius, spacing } from '@/theme';

interface CheckboxProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  hint?: string;
  disabled?: boolean;
}

export function Checkbox({ checked, onChange, label, hint, disabled }: CheckboxProps) {
  return (
    <Pressable
      onPress={() => onChange(!checked)}
      disabled={disabled}
      accessibilityRole="checkbox"
      accessibilityState={{ checked, disabled }}
      accessibilityLabel={label}
      accessibilityHint={hint}
      style={({ pressed }) => [styles.row, { opacity: disabled ? 0.5 : pressed ? 0.8 : 1 }]}>
      <View style={[styles.box, checked ? styles.boxChecked : null]}>
        {checked ? <View style={styles.tick} /> : null}
      </View>
      <View style={styles.text}>
        <Caption color={colors.textPrimary} style={styles.label}>
          {label}
        </Caption>
        {hint ? <Caption>{hint}</Caption> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
  },
  box: {
    width: 26,
    height: 26,
    borderRadius: radius.input,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.card,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  boxChecked: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  tick: {
    width: 12,
    height: 12,
    borderRadius: 3,
    backgroundColor: colors.card,
  },
  text: {
    flex: 1,
    gap: spacing.xs,
  },
  label: {
    fontWeight: '600',
  },
});
