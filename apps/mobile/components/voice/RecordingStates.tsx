import { StyleSheet, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { Caption, Heading } from '@/components/ui/TextBlock';
import { colors, spacing } from '@/theme';
import { RecordingState } from '@/types';

interface RecordingStatesProps {
  state: RecordingState;
  error?: string | null;
}

const COPY: Record<RecordingState, { title: string; detail: string }> = {
  idle: { title: 'Tap to record', detail: 'Say the phrase at a normal pace.' },
  preparing: { title: 'Getting ready…', detail: 'Opening the microphone.' },
  recording: { title: 'Listening…', detail: 'Speak clearly until you stop.' },
  processing: { title: 'Checking recording…', detail: 'Analysing the sample.' },
  success: { title: 'Phrase recorded', detail: 'The temporary sample was deleted.' },
  error: { title: 'Could not record', detail: 'Please try again.' },
};

/**
 * Human-readable status for the current recording state.
 */
export function RecordingStates({ state, error }: RecordingStatesProps) {
  const copy = COPY[state];

  return (
    <Card tone={state === 'error' ? 'danger' : 'muted'}>
      <View style={styles.wrapper}>
        <Heading color={state === 'error' ? colors.danger : colors.textPrimary}>
          {copy.title}
        </Heading>
        <Caption color={state === 'error' ? colors.danger : colors.textSecondary}>
          {state === 'error' && error ? error : copy.detail}
        </Caption>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: spacing.xs,
  },
});
