import { PropsWithChildren } from 'react';
import { ScrollView, StyleSheet, useWindowDimensions, View, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing } from '@/theme';

interface ScreenProps {
  /** Wraps content in a ScrollView. Disable for screens with their own scroll. */
  scrollable?: boolean;
  /** Applies the default horizontal page padding. */
  padded?: boolean;
  contentStyle?: ViewStyle;
  /** narrow: single column for forms (default). wide: laptop layouts. */
  size?: 'narrow' | 'wide';
  testID?: string;
}

export function Screen({
  children,
  scrollable = true,
  padded = true,
  contentStyle,
  size = 'narrow',
  testID,
}: PropsWithChildren<ScreenProps>) {
  const { width } = useWindowDimensions();
  const content = [
    padded && styles.padded,
    padded && width >= 900 && styles.paddedWide,
    styles.content,
    { maxWidth: size === 'wide' ? 1080 : 560 },
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
    width: '100%',
    alignSelf: 'center',
    gap: spacing.lg,
    paddingVertical: spacing.lg,
    flexGrow: 1,
  },
  padded: {
    paddingHorizontal: spacing.lg,
  },
  paddedWide: {
    paddingHorizontal: spacing.xl,
  },
});
