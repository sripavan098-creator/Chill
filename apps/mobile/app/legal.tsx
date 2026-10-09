import { router } from 'expo-router';
import { Linking, StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { PRIVACY_URL, REPO_URL, SECURITY_URL } from '@/lib/config';
import { colors, spacing } from '@/theme';

const PRINCIPLES = [
  {
    title: 'Your voice is biometric data',
    detail:
      'Chill asks for explicit consent before enrollment and never stores raw recordings by default.',
  },
  {
    title: 'Voice is a convenience, not the only lock',
    detail:
      'Sensitive actions need a stronger check. Voice recognition is never the last line of defence.',
  },
  {
    title: 'You stay in control',
    detail:
      'You can withdraw consent, delete your voice profile, or delete your whole account at any time.',
  },
  {
    title: 'No hidden listening',
    detail:
      'Chill does not listen in the background and has no always-on wake word.',
  },
];

/**
 * Legal and privacy summary.
 *
 * This is a plain-language companion to the full documents. Nothing here is a
 * legal claim of security; it points at the same principles the backend
 * enforces.
 */
export default function LegalScreen() {
  const open = (url: string) => {
    void Linking.openURL(url);
  };

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Privacy and terms</Title>
        <Body color={colors.textSecondary}>
          The short version of how Chill treats your voice, with links to the full documents.
        </Body>
      </View>

      <View style={styles.cards}>
        {PRINCIPLES.map((item) => (
          <Card key={item.title}>
            <Heading>{item.title}</Heading>
            <Caption>{item.detail}</Caption>
          </Card>
        ))}
      </View>

      <Card tone="muted">
        <Caption color={colors.primaryDark}>
          What Chill will not claim: that voice sign-in is unbreakable, or that it never
          makes mistakes. Additional verification may be required for sensitive actions.
        </Caption>
      </Card>

      <View style={styles.actions}>
        <Button
          label="Read the privacy policy"
          variant="secondary"
          onPress={() => open(PRIVACY_URL)}
          accessibilityHint="Open the full privacy policy in a browser"
        />
        <Button
          label="Read the security model"
          variant="secondary"
          onPress={() => open(SECURITY_URL)}
          accessibilityHint="Open the security model in a browser"
        />
        <Button
          label="View the source"
          variant="ghost"
          onPress={() => open(REPO_URL)}
          accessibilityHint="Open the Chill repository in a browser"
        />
        <Button label="Back" variant="ghost" onPress={() => router.back()} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: spacing.lg,
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
