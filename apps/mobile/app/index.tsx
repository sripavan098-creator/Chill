import { Redirect } from 'expo-router';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { Caption } from '@/components/ui/TextBlock';
import { useChill } from '@/state/ChillContext';
import { colors, spacing } from '@/theme';

/**
 * Entry gate. Sends the user to login when a voice profile exists,
 * otherwise into onboarding.
 */
export default function IndexScreen() {
  const { hydrated, onboardingComplete } = useChill();

  if (!hydrated) {
    return (
      <View style={styles.loading} accessibilityLabel="Loading Chill">
        <ActivityIndicator color={colors.primary} size="large" />
        <Caption>Waking up Chill…</Caption>
      </View>
    );
  }

  return <Redirect href={onboardingComplete ? '/login' : '/welcome'} />;
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
    backgroundColor: colors.background,
  },
});
