import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { colors, spacing } from '@/theme';

const HIGHLIGHTS = [
  {
    title: 'Recognizes you by voice',
    detail: 'Chill learns a private voice profile from five short phrases.',
  },
  {
    title: 'Privacy first',
    detail: 'No raw recordings are kept and you can delete your voice profile anytime.',
  },
  {
    title: 'Always a fallback',
    detail: 'Voice is a convenience layer. A PIN backup is always available.',
  },
];

export default function WelcomeScreen() {
  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.hero}>
        <View style={styles.mark}>
          <View style={styles.markInner} />
        </View>
        <Title center>Welcome to Chill</Title>
        <Body center color={colors.textSecondary}>
          A calm personal assistant that recognizes its owner by voice.
        </Body>
      </View>

      <View style={styles.cards}>
        {HIGHLIGHTS.map((item) => (
          <Card key={item.title}>
            <Heading>{item.title}</Heading>
            <Caption>{item.detail}</Caption>
          </Card>
        ))}
      </View>

      <View style={styles.actions}>
        <Button
          label="Get started"
          onPress={() => router.push('/permissions')}
          accessibilityHint="Continue to microphone permission setup"
        />
        <Caption center>
          By continuing you agree to the voice privacy principles in docs/PRIVACY.md.
        </Caption>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    justifyContent: 'space-between',
  },
  hero: {
    alignItems: 'center',
    gap: spacing.md,
    marginTop: spacing.xl,
  },
  mark: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  markInner: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
  },
  cards: {
    gap: spacing.md,
  },
  actions: {
    gap: spacing.md,
  },
});
