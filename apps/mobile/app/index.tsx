import { Redirect } from 'expo-router';
import { ActivityIndicator, Linking, StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Title } from '@/components/ui/TextBlock';
import { useChill } from '@/state/ChillContext';
import { colors, spacing } from '@/theme';

/**
 * Entry gate. Sends the user to login when a voice profile exists,
 * otherwise into onboarding. A backend that has retired this build shows a
 * blocking update screen first; the check fails open, so it never traps a user
 * offline.
 */
export default function IndexScreen() {
  const { hydrated, onboardingComplete, version } = useChill();

  if (!hydrated) {
    return (
      <View style={styles.loading} accessibilityLabel="Loading Chill">
        <ActivityIndicator color={colors.primary} size="large" />
        <Caption>Waking up Chill…</Caption>
      </View>
    );
  }

  if (version?.status === 'update-required') {
    return (
      <Screen contentStyle={styles.content}>
        <View style={styles.header}>
          <Title>Update required</Title>
          <Body color={colors.textSecondary}>{version.message}</Body>
        </View>
        <Card tone="muted">
          <Caption color={colors.warning}>
            Your voice profile and settings stay on this device until you update.
          </Caption>
        </Card>
        <Button
          label="Open the update page"
          onPress={() => {
            if (version.updateUrl) void Linking.openURL(version.updateUrl);
          }}
          accessibilityHint="Open the update page in a browser"
        />
      </Screen>
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
  content: {
    justifyContent: 'center',
  },
  header: {
    gap: spacing.sm,
  },
});
