import { StyleSheet, TextInput, TextInputProps, View } from 'react-native';

import { Caption } from '@/components/ui/TextBlock';
import { colors, radius, spacing, typography } from '@/theme';

interface TextFieldProps extends TextInputProps {
  label: string;
  hint?: string;
  error?: string;
}

export function TextField({ label, hint, error, style, ...rest }: TextFieldProps) {
  return (
    <View style={styles.wrapper}>
      <Caption color={colors.textPrimary} style={styles.label}>
        {label}
      </Caption>
      <TextInput
        style={[styles.input, error ? styles.inputError : null, style]}
        placeholderTextColor={colors.textSecondary}
        accessibilityLabel={label}
        {...rest}
      />
      {error ? (
        <Caption color={colors.danger}>{error}</Caption>
      ) : hint ? (
        <Caption>{hint}</Caption>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: spacing.sm,
  },
  label: {
    fontWeight: '600',
  },
  input: {
    ...typography.body,
    borderRadius: radius.input,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    backgroundColor: colors.card,
    paddingVertical: 14,
    paddingHorizontal: spacing.md,
  },
  inputError: {
    borderColor: colors.danger,
    borderWidth: 1.5,
  },
});
