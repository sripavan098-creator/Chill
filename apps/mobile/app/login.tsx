import { router } from 'expo-router';
import { useEffect } from 'react';
import { StyleSheet, Switch, View } from 'react-native';

import { Badge, InfoRow } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { MicButton } from '@/components/voice/MicButton';
import { RecordingTimer } from '@/components/voice/RecordingTimer';
import { useVoiceVerification } from '@/features/voice-auth/useVoiceVerification';
import { useMicrophonePermission } from '@/hooks/useMicrophonePermission';
import { colors, spacing } from '@/theme';

const LOGIN_MAX_RECORDING_MS = 3000;

export default function LoginScreen() {
  const {
    hasProfile,
    phase,
    busy,
    elapsedMs,
    result,
    error,
    phrase,
    attemptLimitReached,
    simulateFailure,
    setSimulateFailure,
    verify,
  } = useVoiceVerification();

  const permission = useMicrophonePermission();
  const succeeded = phase === 'result' && result?.outcome === 'success';

  useEffect(() => {
    if (succeeded) router.replace('/home');
  }, [succeeded]);

  const onPressMic = async () => {
    if (!permission.granted) {
      const next = await permission.request();
      if (next !== 'granted') return;
    }
    await verify();
  };

  const caption = busy
    ? phase === 'verifying'
      ? 'Checking your voice…'
      : 'Listening…'
    : 'Tap to speak';

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Voice sign-in</Title>
        <Body color={colors.textSecondary}>
          {busy
            ? 'Listening for your voice…'
            : 'Speak the challenge phrase to confirm it is you.'}
        </Body>
      </View>

      {phrase ? (
        <Card>
          <Heading>Say this phrase</Heading>
          <Body color={colors.primary}>{phrase}</Body>
          <Caption>
            Chill asks for a new phrase each time. It is checked with speech
            recognition and helps reject a replayed recording.
          </Caption>
        </Card>
      ) : null}

      <View style={styles.micArea}>
        <MicButton
          onPress={onPressMic}
          active={busy}
          disabled={busy || !hasProfile || permission.denied}
          caption={caption}
          accessibilityLabel="Start voice verification"
        />
        {phase === 'listening' ? (
          <RecordingTimer
            elapsedMs={elapsedMs}
            maxMs={LOGIN_MAX_RECORDING_MS}
            active
          />
        ) : null}
      </View>

      {permission.denied ? (
        <Card tone="danger">
          <Heading color={colors.danger}>Microphone access is needed</Heading>
          <Caption color={colors.danger}>
            Chill uses your microphone only to enroll and recognize your voice. Enable
            microphone permission in your device settings to sign in with voice.
          </Caption>
          <Button
            label="Open settings"
            variant="secondary"
            onPress={permission.openSettings}
            accessibilityHint="Open the device settings for Chill"
          />
          <Button
            label="Use PIN instead"
            variant="ghost"
            onPress={() => router.push('/fallback')}
          />
        </Card>
      ) : null}

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
    gap: spacing.md,
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
