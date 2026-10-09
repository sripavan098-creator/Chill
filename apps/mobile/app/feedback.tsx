import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Checkbox } from '@/components/ui/Checkbox';
import { Screen } from '@/components/ui/Screen';
import { TextField } from '@/components/ui/TextField';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { APP_VERSION } from '@/lib/appVersion';
import { useChill } from '@/state/ChillContext';
import { FeedbackKind } from '@/types';
import { colors, spacing } from '@/theme';

const KINDS: { id: FeedbackKind; label: string }[] = [
  { id: 'general', label: 'General feedback' },
  { id: 'bug', label: 'Something is broken' },
  { id: 'idea', label: 'An idea' },
  { id: 'privacy', label: 'A privacy concern' },
];

/**
 * Beta feedback. Deliberately collects only a short note plus the app version
 * and platform: no audio, no voice data. The privacy concern option is
 * surfaced as a first-class choice so it does not get buried in "general".
 */
export default function FeedbackScreen() {
  const { submitFeedback } = useChill();
  const [kind, setKind] = useState<FeedbackKind>('general');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = message.trim();
  const canSend = trimmed.length >= 5 && !busy;

  const onSend = async () => {
    if (!canSend) return;
    setBusy(true);
    setError(null);
    try {
      await submitFeedback(kind, trimmed);
      setSent(true);
      setMessage('');
    } catch {
      setError('We could not send your feedback. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Beta feedback</Title>
        <Body color={colors.textSecondary}>
          Tell us what is working and what is not. This helps the beta.
        </Body>
      </View>

      {sent ? (
        <Card tone="success">
          <Heading color={colors.success}>Thank you</Heading>
          <Caption color={colors.success}>
            Your note was recorded. If it was a privacy concern, we will look at it first.
          </Caption>
          <Button label="Send another" variant="secondary" onPress={() => setSent(false)} />
        </Card>
      ) : (
        <>
          <Card>
            <Heading>What is this about?</Heading>
            <View style={styles.kinds}>
              {KINDS.map((option) => (
                <Checkbox
                  key={option.id}
                  checked={kind === option.id}
                  onChange={() => setKind(option.id)}
                  label={option.label}
                />
              ))}
            </View>
          </Card>

          <Card>
            <TextField
              label="Your note"
              value={message}
              onChangeText={setMessage}
              placeholder="What happened, or what would help?"
              multiline
              numberOfLines={5}
              maxLength={2000}
              editable={!busy}
              hint={`${trimmed.length}/2000`}
              accessibilityHint="Describe your feedback in a few sentences"
            />
            <Caption color={colors.textSecondary}>
              Please do not include passwords, voice recordings, or other sensitive data.
            </Caption>
          </Card>

          <Card tone="muted">
            <Caption color={colors.primaryDark}>
              Sent with app version {APP_VERSION} and your platform only. No audio or voice
              data is attached.
            </Caption>
          </Card>

          {error ? <Caption color={colors.danger}>{error}</Caption> : null}

          <View style={styles.actions}>
            <Button
              label="Send feedback"
              onPress={onSend}
              disabled={!canSend}
              loading={busy}
              accessibilityHint="Send the feedback to the Chill team"
            />
            <Button label="Back" variant="ghost" onPress={() => router.back()} disabled={busy} />
          </View>
        </>
      )}
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
  kinds: {
    gap: spacing.md,
  },
  actions: {
    gap: spacing.sm,
  },
});
