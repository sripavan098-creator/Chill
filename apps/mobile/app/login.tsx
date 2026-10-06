import { router } from 'expo-router';
import { useEffect } from 'react';
import { StyleSheet, Switch, View } from 'react-native';

import { Badge, InfoRow } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { MicButton } from '@/components/voice/MicButton';
import { useVoiceVerification } from '@/features/voice-auth/useVoiceVerification';
import { colors, spacing } from '@/theme';

export default function LoginScreen() {
  const {
    hasProfile,
    phase,
    busy,
    result,
    error,
    attemptLimitReached,
    simulateFailure,
    setSimulateFailure,
    verify,
  } = useVoiceVerification();

  const succeeded = phase === 'result' && result?.outcome === 'success';

  useEffect(() => {
    if (succeeded) router.replace('/home');
  }, [succeeded]);

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Voice sign-in</Title>
        <Body color={colors.textSecondary}>
          {busy
            ? 'Listening for your voice…'
            : 'Tap the microphone and say: “Hey Chill, unlock my assistant.”'}
        </Body>
      </View>

      <View style={styles.micArea}>
        <MicButton
          onPress={verify}
          active={busy}
          disabled={busy || !hasProfile}
          caption={phase === 'verifying' ? 'Checking your voice…' : 'Tap to speak'}
          accessibilityLabel="Start mock voice verification"
        />
      </View>

      {!hasProfile ? (
        <Card tone="danger">
          <Caption color={colors.danger}>
            No voice profile found. Complete enrollment before signing in with voice.
          </Caption>
        </Card>
      ) : null}

      {phase === 'result' && result ? (
        <Card tone={result.outcome === 'success' ? 'success' : 'default'}>
          <View style={styles.resultHeader}>
            <Heading>Verification result</Heading>
            <Badge
              label={result.outcome === 'success' ? 'Matched' : 'No match'}
              tone={result.outcome === 'success' ? 'success' : 'danger'}
            />
          </View>
          <InfoRow label="Confidence" value={result.confidence.toFixed(2)} />
          <InfoRow label="Attempts left" value={`${result.attemptsRemaining}`} />
          <Caption>{result.reason}</Caption>
        </Card>
      ) : null}

      {error ? <Caption color={colors.danger}>{error}</Caption> : null}

      {attemptLimitReached ? (
        <Card tone="danger">
          <Caption color={colors.danger}>
            Attempt limit reached. Use your PIN backup to continue.
          </Caption>
        </Card>
      ) : null}

      <Card>
        <View style={styles.devHeader}>
          <Heading>Developer options</Heading>
          <Badge label="Mock" tone="warning" />
        </View>
        <Caption>
          Force the next mock verification to fail so you can test the fallback path.
        </Caption>
        <View style={styles.switchRow}>
          <Body>Simulate failure</Body>
          <Switch
            value={simulateFailure}
            onValueChange={setSimulateFailure}
            trackColor={{ false: colors.border, true: colors.primary }}
            thumbColor={colors.card}
            accessibilityLabel="Simulate voice verification failure"
          />
        </View>
      </Card>

      <View style={styles.actions}>
        <Button
          label="Use PIN instead"
          variant="secondary"
          onPress={() => router.push('/fallback')}
          accessibilityHint="Open the fallback PIN screen"
        />
        <Button
          label="Delete voice profile"
          variant="ghost"
          onPress={() => router.push('/settings')}
          accessibilityHint="Open settings to manage your voice profile"
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
  micArea: {
    alignItems: 'center',
    paddingVertical: spacing.lg,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.sm,
  },
  devHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
  },
  actions: {
    gap: spacing.sm,
  },
});
