import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Checkbox } from '@/components/ui/Checkbox';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { useOnboarding } from '@/features/onboarding/useOnboarding';
import { colors, spacing } from '@/theme';

const CONSENT_ITEMS = [
  {
    id: 'process',
    label: 'I consent to Chill processing my voice to create a voice profile.',
    hint: 'Voice is biometric data. Processing is required to recognize you.',
  },
  {
    id: 'storage',
    label: 'I understand that raw recordings are not stored by default.',
    hint: 'Only a derived voice profile would be stored in a later milestone.',
  },
  {
    id: 'delete',
    label: 'I understand that I can delete my voice profile at any time.',
    hint: 'Deletion is available in Settings and takes effect immediately.',
  },
];

export default function ConsentScreen() {
  const { grant } = useOnboarding();
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allAccepted = CONSENT_ITEMS.every((item) => accepted[item.id]);

  const toggle = (id: string, next: boolean) => {
    setAccepted((prev) => ({ ...prev, [id]: next }));
  };

  const onContinue = async () => {
    if (!allAccepted) return;
    setSubmitting(true);
    setError(null);
    try {
      await grant();
      router.push('/enroll');
    } catch {
      setError('We could not save your consent. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Voice consent</Title>
        <Body color={colors.textSecondary}>
          Chill only processes your voice if you explicitly agree. Read and confirm each point
          below.
        </Body>
      </View>

      <Card>
        <Heading>What you are agreeing to</Heading>
        <View style={styles.items}>
          {CONSENT_ITEMS.map((item) => (
            <Checkbox
              key={item.id}
              checked={Boolean(accepted[item.id])}
              onChange={(next) => toggle(item.id, next)}
              label={item.label}
              hint={item.hint}
            />
          ))}
        </View>
      </Card>

      <Card tone="muted">
        <Caption color={colors.primaryDark}>
          You can withdraw consent and delete your voice profile from Settings at any time.
        </Caption>
      </Card>

      {error ? <Caption color={colors.danger}>{error}</Caption> : null}

      <View style={styles.actions}>
        <Button
          label="Agree and continue"
          onPress={onContinue}
          disabled={!allAccepted}
          loading={submitting}
          accessibilityHint="Save consent and continue to voice enrollment"
        />
        <Button
          label="Go back"
          variant="ghost"
          onPress={() => router.back()}
          disabled={submitting}
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
  items: {
    gap: spacing.lg,
  },
  actions: {
    gap: spacing.sm,
  },
});
