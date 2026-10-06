import { StyleSheet, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Body, Caption } from '@/components/ui/TextBlock';
import { colors, spacing } from '@/theme';
import { EnrollmentClip, EnrollmentPhrase } from '@/types';

interface PhraseCardProps {
  phrase: EnrollmentPhrase;
  clip: EnrollmentClip;
  active: boolean;
  disabled?: boolean;
  onRecord: () => void;
  onRetry: () => void;
}

const STATUS_LABEL: Record<EnrollmentClip['status'], string> = {
  idle: 'Not recorded',
  recording: 'Recording',
  recorded: 'Captured',
  error: 'Try again',
};

const STATUS_TONE: Record<EnrollmentClip['status'], 'info' | 'warning' | 'success' | 'danger'> = {
  idle: 'info',
  recording: 'warning',
  recorded: 'success',
  error: 'danger',
};

export function PhraseCard({
  phrase,
  clip,
  active,
  disabled,
  onRecord,
  onRetry,
}: PhraseCardProps) {
  const isRecorded = clip.status === 'recorded';
  const isRecording = clip.status === 'recording';

  return (
    <Card
      tone={isRecorded ? 'success' : 'default'}
      style={active ? styles.active : undefined}
      testID={`phrase-card-${phrase.id}`}>
      <View style={styles.header}>
        <Caption>{`Phrase ${phrase.index + 1} of 5`}</Caption>
        <Badge label={STATUS_LABEL[clip.status]} tone={STATUS_TONE[clip.status]} />
      </View>

      <Body style={styles.phrase}>{`"${phrase.text}"`}</Body>

      {clip.durationMs != null && isRecorded ? (
        <Caption>{`Sample length ${(clip.durationMs / 1000).toFixed(1)}s`}</Caption>
      ) : null}

      {clip.error ? <Caption color={colors.danger}>{clip.error}</Caption> : null}

      <View style={styles.actions}>
        {isRecorded ? (
          <Button
            label="Retry phrase"
            variant="secondary"
            onPress={onRetry}
            accessibilityHint={`Re-record phrase ${phrase.index + 1}`}
            style={styles.action}
          />
        ) : (
          <Button
            label={isRecording ? 'Recording…' : 'Record phrase'}
            variant={isRecording ? 'secondary' : 'primary'}
            onPress={onRecord}
            loading={isRecording}
            disabled={disabled || isRecording}
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
