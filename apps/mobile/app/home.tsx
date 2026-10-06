import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { useChill } from '@/state/ChillContext';
import { colors, spacing } from '@/theme';

const CAPABILITIES = [
  { title: 'Ask anything', detail: 'Chat with Chill about your day, plans, or notes.' },
  { title: 'Private by default', detail: 'Nothing is stored without your consent.' },
  { title: 'Voice sign-in', detail: 'Recognized as the owner after a quick voice check.' },
];

export default function HomeScreen() {
  const { voiceProfile, consent } = useChill();

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <View style={styles.greetingRow}>
          <Title>{`Hi, ${voiceProfile?.displayName ?? 'there'}`}</Title>
          <Badge
            label={consent?.granted ? 'Voice on' : 'Voice off'}
            tone={consent?.granted ? 'success' : 'warning'}
          />
        </View>
        <Body color={colors.textSecondary}>
          Chill is ready. This is the v0.1 assistant home placeholder.
        </Body>
      </View>

      <Card tone="muted">
        <Heading>Try saying</Heading>
        <Caption color={colors.primaryDark}>“Hey Chill, what is on my schedule?”</Caption>
      </Card>

      <View style={styles.cards}>
        {CAPABILITIES.map((item) => (
          <Card key={item.title}>
            <Heading>{item.title}</Heading>
            <Caption>{item.detail}</Caption>
          </Card>
        ))}
      </View>

      <Card>
        <Caption>
          Assistant conversations are not implemented in v0.1. The next milestones add real
          recording, a backend, and speaker verification.
        </Caption>
      </Card>

      <View style={styles.actions}>
        <Button
          label="Lock and sign in again"
          variant="secondary"
          onPress={() => router.replace('/login')}
          accessibilityHint="Return to the voice sign-in screen"
        />
        <Button
          label="Settings"
          variant="ghost"
          onPress={() => router.push('/settings')}
          accessibilityHint="Open settings and privacy controls"
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
  greetingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
  },
  cards: {
    gap: spacing.md,
  },
  actions: {
    gap: spacing.sm,
  },
});
