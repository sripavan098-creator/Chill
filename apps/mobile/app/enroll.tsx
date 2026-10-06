import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { TextField } from '@/components/ui/TextField';
import { Body, Caption, Title } from '@/components/ui/TextBlock';
import { EnrollmentProgress } from '@/components/voice/EnrollmentProgress';
import { PhraseCard } from '@/components/voice/PhraseCard';
import { useEnrollment } from '@/features/voice-auth/useEnrollment';
import { useChill } from '@/state/ChillContext';
import { colors, spacing } from '@/theme';

export default function EnrollScreen() {
  const { consent } = useChill();
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const {
    phrases,
    clips,
    activePhraseId,
    isRecording,
    completedCount,
    total,
    allComplete,
    finishing,
    start,
    stop,
    retry,
    reset,
    submit,
  } = useEnrollment();

  const onFinish = async () => {
    setError(null);
    try {
      await submit(displayName);
      router.replace('/enroll-success');
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'We could not create your voice profile. Please try again.',
      );
    }
  };

  const onReset = () => {
    setError(null);
    reset();
  };

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Voice enrollment</Title>
        <Body color={colors.textSecondary}>
          Record the five phrases below. Each sample is checked for length, then the
          temporary recording is deleted.
        </Body>
      </View>

      {!consent?.granted ? (
        <Card tone="danger">
          <Caption color={colors.danger}>
            Voice consent is missing. Go back and confirm the consent screen before enrolling.
          </Caption>
        </Card>
      ) : null}

      <Card>
        <TextField
          label="Owner name"
          value={displayName}
          onChangeText={setDisplayName}
          placeholder="What should Chill call you?"
          hint="Optional. Defaults to “Chill owner”."
          autoCapitalize="words"
          returnKeyType="done"
          editable={!isRecording}
        />
      </Card>

      <EnrollmentProgress completed={completedCount} total={total} />

      <View style={styles.phrases}>
        {phrases.map((phrase) => {
          const clip = clips.find((item) => item.phraseId === phrase.id);
          if (!clip) return null;
          return (
            <PhraseCard
              key={phrase.id}
              phrase={phrase}
              clip={clip}
              active={activePhraseId === phrase.id}
              disabled={isRecording && activePhraseId !== phrase.id}
              onRecord={() => start(phrase.id)}
              onStop={stop}
              onRetry={() => retry(phrase.id)}
            />
          );
        })}
      </View>

      {error ? <Caption color={colors.danger}>{error}</Caption> : null}

      <View style={styles.actions}>
        <Button
          label={allComplete ? 'Create my voice profile' : `Record all ${total} phrases`}
          onPress={onFinish}
          disabled={!allComplete || !consent?.granted || isRecording}
          loading={finishing}
          accessibilityHint="Create the mock owner voice profile"
        />
        <Button
          label="Start over"
          variant="ghost"
          onPress={onReset}
          disabled={isRecording || finishing || completedCount === 0}
        />
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
  phrases: {
    gap: spacing.md,
  },
  actions: {
    gap: spacing.sm,
  },
});
