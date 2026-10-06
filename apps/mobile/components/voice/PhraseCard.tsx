import { StyleSheet, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Body, Caption } from '@/components/ui/TextBlock';
import { RecordingTimer } from '@/components/voice/RecordingTimer';
import { MAX_RECORDING_MS, MIN_RECORDING_MS } from '@/features/voice-auth/validation';
import { colors, spacing } from '@/theme';
import { EnrollmentClip, EnrollmentPhrase } from '@/types';

interface PhraseCardProps {
  phrase: EnrollmentPhrase;
  clip: EnrollmentClip;
  active: boolean;
  disabled?: boolean;
  onRecord: () => void;
  onStop: () => void;
  onRetry: () => void;
}

const STATUS_LABEL: Record<EnrollmentClip['status'], string> = {
  idle: 'Not recorded',
  preparing: 'Preparing',
  recording: 'Recording',
  processing: 'Checking',
  recorded: 'Captured',
  error: 'Try again',
};

const STATUS_TONE: Record<
  EnrollmentClip['status'],
  'info' | 'warning' | 'success' | 'danger'
> = {
  idle: 'info',
  preparing: 'warning',
  recording: 'warning',
  processing: 'info',
  recorded: 'success',
  error: 'danger',
};

export function PhraseCard({
  phrase,
  clip,
  active,
  disabled,
  onRecord,
  onStop,
  onRetry,
}: PhraseCardProps) {
  const isRecorded = clip.status === 'recorded';
  const isBusy =
    clip.status === 'preparing' ||
    clip.status === 'recording' ||
    clip.status === 'processing';
  const isRecording = clip.status === 'recording';

  return (
    <Card
      tone={isRecorded ? 'success' : 'default'}
      style={active ? styles.active : undefined}
      testID={`phrase-card-${phrase.id}`}>
      <View style={styles.header}>
        <Caption>{`Phrase ${phrase.index + 1} of 5`}</Caption>
        <View testID={`phrase-status-${phrase.id}`}>
          <Badge label={STATUS_LABEL[clip.status]} tone={STATUS_TONE[clip.status]} />
        </View>
      </View>

      <Body style={styles.phrase}>{`"${phrase.text}"`}</Body>

      {isRecording || clip.status === 'preparing' ? (
        <RecordingTimer
          elapsedMs={clip.durationMs ?? 0}
          maxMs={MAX_RECORDING_MS}
          active={isRecording}
        />
      ) : null}

      {isRecorded && clip.durationMs != null ? (
        <Caption>{`Sample length ${(clip.durationMs / 1000).toFixed(1)}s`}</Caption>
      ) : null}

      {clip.status === 'processing' ? (
        <Caption color={colors.textSecondary}>Checking recording…</Caption>
      ) : null}

      {clip.error ? <Caption color={colors.danger}>{clip.error}</Caption> : null}

      {clip.status === 'idle' && !isRecorded ? (
        <Caption>{`Hold the phrase for at least ${(MIN_RECORDING_MS / 1000).toFixed(1)}s.`}</Caption>
      ) : null}

      <View style={styles.actions}>
        {isRecorded ? (
          <Button
            label="Retry phrase"
            variant="secondary"
            onPress={onRetry}
            accessibilityHint={`Re-record phrase ${phrase.index + 1}`}
            style={styles.action}
          />
        ) : isRecording ? (
          <Button
            label="Stop recording"
            variant="danger"
            onPress={onStop}
            accessibilityHint={`Stop recording phrase ${phrase.index + 1}`}
            style={styles.action}
          />
        ) : (
          <Button
            label={clip.status === 'processing' ? 'Checking…' : 'Record phrase'}
            variant="primary"
            onPress={onRecord}
            loading={isBusy}
            disabled={disabled || isBusy}
            accessibilityHint={`Record phrase ${phrase.index + 1}`}
            style={styles.action}
          />
        )}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  active: {
    borderColor: colors.primary,
    borderWidth: 1.5,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.sm,
  },
  phrase: {
    fontStyle: 'italic',
  },
  actions: {
    flexDirection: 'row',
  },
  action: {
    flex: 1,
  },
});
