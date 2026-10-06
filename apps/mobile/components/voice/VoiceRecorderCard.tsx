import { StyleSheet, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { Body } from '@/components/ui/TextBlock';
import { MicButton } from '@/components/voice/MicButton';
import { RecordingStates } from '@/components/voice/RecordingStates';
import { RecordingTimer } from '@/components/voice/RecordingTimer';
import { colors, spacing } from '@/theme';
import { RecordingState } from '@/types';

interface VoiceRecorderCardProps {
  state: RecordingState;
  elapsedMs: number;
  maxMs: number;
  error?: string | null;
  prompt?: string;
  onStart: () => void;
  onStop: () => void;
  disabled?: boolean;
}

const IDLE_CAPTION = 'Tap to record';

/**
 * Reusable recorder card: mic button, timer and status copy for one session.
 */
export function VoiceRecorderCard({
  state,
  elapsedMs,
  maxMs,
  error,
  prompt,
  onStart,
  onStop,
  disabled = false,
}: VoiceRecorderCardProps) {
  const isRecording = state === 'recording';
  const busy = state === 'preparing' || state === 'processing';

  return (
    <Card>
      <View style={styles.wrapper}>
        {prompt ? (
          <Body color={colors.textSecondary} center>
            {prompt}
          </Body>
        ) : null}

        <MicButton
          onPress={isRecording ? onStop : onStart}
          active={isRecording}
          disabled={disabled || busy}
          caption={isRecording ? 'Tap to stop' : IDLE_CAPTION}
          accessibilityLabel={isRecording ? 'Stop recording' : 'Start recording'}
        />

        <RecordingTimer elapsedMs={elapsedMs} maxMs={maxMs} active={isRecording} />
        <RecordingStates state={state} error={error} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    gap: spacing.md,
  },
});
