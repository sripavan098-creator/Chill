import { PropsWithChildren } from 'react';
import { ScrollView, StyleSheet, View, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing } from '@/theme';

interface ScreenProps {
  /** Wraps content in a ScrollView. Disable for screens with their own scroll. */
  scrollable?: boolean;
  /** Applies the default horizontal page padding. */
  padded?: boolean;
  contentStyle?: ViewStyle;
  testID?: string;
}

export function Screen({
  children,
  scrollable = true,
  padded = true,
  contentStyle,
  testID,
}: PropsWithChildren<ScreenProps>) {
  const content = [
    padded && styles.padded,
    styles.content,
    contentStyle,
  ];

  if (!scrollable) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']} testID={testID}>
        <View style={[styles.flex, content]}>{children}</View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']} testID={testID}>
      <ScrollView
        contentContainerStyle={content}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}>
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  flex: {
    flex: 1,
  },
  content: {
    gap: spacing.lg,
    paddingVertical: spacing.lg,
    flexGrow: 1,
  },
  padded: {
    paddingHorizontal: spacing.lg,
  },
});
