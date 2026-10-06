import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { colors, spacing } from '@/theme';

const PERMISSION_POINTS = [
  {
    title: 'Used only during setup',
    detail: 'The microphone is active while you record enrollment phrases and when you sign in.',
  },
  {
    title: 'Never always-on',
    detail: 'Chill does not listen in the background and has no wake word in v0.1.',
  },
  {
    title: 'No raw audio kept',
    detail: 'Recordings are processed for the voice profile only. Raw audio is not stored.',
  },
];

export default function PermissionsScreen() {
  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Microphone access</Title>
        <Body color={colors.textSecondary}>
          Chill needs your microphone to learn your voice. Here is exactly what that means.
        </Body>
      </View>

      <View style={styles.cards}>
        {PERMISSION_POINTS.map((point) => (
          <Card key={point.title}>
            <Heading>{point.title}</Heading>
            <Caption>{point.detail}</Caption>
          </Card>
        ))}
      </View>

      <Card tone="muted">
        <Caption color={colors.primaryDark}>
          v0.1 uses a mock recorder. No microphone permission is requested yet — this screen
          explains what will happen in the next milestone.
        </Caption>
      </Card>

      <View style={styles.actions}>
        <Button
          label="I understand, continue"
          onPress={() => router.push('/consent')}
          accessibilityHint="Continue to the voice consent screen"
        />
        <Button
          label="Not now"
          variant="ghost"
          onPress={() => router.replace('/welcome')}
          accessibilityHint="Return to the welcome screen"
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    justifyContent: 'space-between',
  },
  header: {
    gap: spacing.sm,
  },
  cards: {
    gap: spacing.md,
  },
  actions: {
    gap: spacing.sm,
  },
});
