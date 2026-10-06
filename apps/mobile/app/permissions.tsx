import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { useMicrophonePermission } from '@/hooks/useMicrophonePermission';
import { colors, spacing } from '@/theme';

const PERMISSION_POINTS = [
  {
    title: 'Used only during setup',
    detail: 'The microphone is active while you record enrollment phrases and when you sign in.',
  },
  {
    title: 'Never always-on',
    detail: 'Chill does not listen in the background and has no wake word in v0.2.',
  },
  {
    title: 'No raw audio kept',
    detail:
      'Recordings are checked for length, then the temporary file is deleted. Raw audio is not stored.',
  },
];

export default function PermissionsScreen() {
  const permission = useMicrophonePermission();

  const onAllow = async () => {
    if (permission.granted) {
      router.push('/consent');
      return;
    }
    const next = await permission.request();
    if (next === 'granted') {
      router.push('/consent');
    }
  };

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

      {permission.denied ? (
        <Card tone="danger">
          <Heading color={colors.danger}>Microphone access is needed</Heading>
          <Caption color={colors.danger}>
            Chill uses your microphone only to enroll and recognize your voice. If you denied
            access, please enable microphone permission in your device settings.
          </Caption>
          <Button
            label="Try again"
            variant="secondary"
            onPress={permission.refresh}
            accessibilityHint="Check the microphone permission again"
          />
          <Button
            label="Open settings"
            variant="secondary"
            onPress={permission.openSettings}
            accessibilityHint="Open the device settings for Chill"
          />
          <Button
            label="Continue without voice"
            variant="ghost"
            onPress={() => router.push('/fallback')}
            accessibilityHint="Continue to the PIN fallback placeholder"
          />
        </Card>
      ) : null}

      {permission.error ? (
        <Caption color={colors.danger}>{permission.error}</Caption>
      ) : null}

      {permission.granted ? (
        <Card tone="success">
          <Caption color={colors.success}>
            Microphone access granted. Chill is ready to record enrollment phrases.
          </Caption>
        </Card>
      ) : null}

      <View style={styles.actions}>
        <Button
          label="Allow microphone"
          onPress={onAllow}
          loading={permission.requesting || permission.checking}
          accessibilityHint="Request microphone access and continue to voice consent"
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
