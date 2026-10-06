import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { TextField } from '@/components/ui/TextField';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { useChill } from '@/state/ChillContext';
import { colors, spacing } from '@/theme';

/**
 * Placeholder for the PIN fallback flow.
 *
 * v0.1 does not store or validate a PIN. This screen exists to prove the
 * fallback path is reachable and to reserve the route for Milestone 2.
 */
export default function FallbackScreen() {
  const { voiceProfile } = useChill();
  const [pin, setPin] = useState('');

  const canContinue = pin.trim().length >= 4;

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Use your PIN</Title>
        <Body color={colors.textSecondary}>
          Voice did not match. You can continue with a PIN backup instead.
        </Body>
      </View>

      <Card>
        <Heading>PIN fallback</Heading>
        <TextField
          label="PIN"
          value={pin}
          onChangeText={(text) => setPin(text.replace(/[^0-9]/g, '').slice(0, 8))}
          placeholder="Enter at least 4 digits"
          keyboardType="number-pad"
          secureTextEntry
          maxLength={8}
          hint="Placeholder only. No PIN is stored in v0.1."
        />
        <Caption color={colors.warning}>
          This is a mock screen. PIN verification is not implemented yet.
        </Caption>
      </Card>

      <Card tone="muted">
        <Caption color={colors.primaryDark}>
          Signed in as {voiceProfile?.displayName ?? 'Chill owner'}.
        </Caption>
      </Card>

      <View style={styles.actions}>
        <Button
          label="Continue to home"
          onPress={() => router.replace('/home')}
          disabled={!canContinue}
          accessibilityHint="Continue to the assistant home screen"
        />
        <Button
          label="Try voice again"
          variant="secondary"
          onPress={() => router.replace('/login')}
        />
        <Button label="Back" variant="ghost" onPress={() => router.back()} />
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
  actions: {
    gap: spacing.sm,
  },
});
