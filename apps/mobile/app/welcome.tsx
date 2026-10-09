import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { TwoPane } from '@/components/ui/TwoPane';
import { VoiceOrb } from '@/components/voice/VoiceOrb';
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
    <Screen size="wide" contentStyle={styles.content}>
      <TwoPane visual={(wide) => <VoiceOrb state="idle" size={wide ? 420 : 220} />}>
        <View style={styles.hero}>
          <Title>Welcome to Chill</Title>
          <Body color={colors.textSecondary}>
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
          <Caption>
            By continuing you agree to the voice privacy principles in docs/PRIVACY.md.
          </Caption>
        </View>
      </TwoPane>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    justifyContent: 'center',
  },
  hero: {
    gap: spacing.sm,
  },
  cards: {
    gap: spacing.md,
  },
  actions: {
    gap: spacing.md,
  },
});
