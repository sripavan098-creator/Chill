import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { InfoRow } from '@/components/ui/Badge';
import { Body, Caption, Title } from '@/components/ui/TextBlock';
import { useChill } from '@/state/ChillContext';
import { colors, spacing } from '@/theme';

export default function EnrollSuccessScreen() {
  const { voiceProfile } = useChill();

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.hero}>
        <View style={styles.mark}>
          <View style={styles.markInner} />
        </View>
        <Title center>You are enrolled</Title>
        <Body center color={colors.textSecondary}>
          Chill created a mock owner voice profile. Voice sign-in is ready to try.
        </Body>
      </View>

      <Card>
        <InfoRow label="Profile" value={voiceProfile?.displayName ?? 'Chill owner'} />
        <InfoRow label="Phrases captured" value={`${voiceProfile?.phraseCount ?? 5} of 5`} />
        <InfoRow
          label="Profile created"
          value={
            voiceProfile
              ? new Date(voiceProfile.createdAt).toLocaleDateString()
              : 'Just now'
          }
        />
        <InfoRow label="Raw audio stored" value="None" tone="success" />
      </Card>

      <Card tone="muted">
        <Caption color={colors.primaryDark}>
          This is a mock profile. No real audio was recorded and nothing left your device.
        </Caption>
      </Card>

      <View style={styles.actions}>
        <Button
          label="Continue to voice sign-in"
          onPress={() => router.replace('/login')}
          accessibilityHint="Go to the mock voice login screen"
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    justifyContent: 'space-between',
  },
  hero: {
    alignItems: 'center',
    gap: spacing.md,
    marginTop: spacing.xl,
  },
  mark: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.successSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  markInner: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.success,
  },
  actions: {
    gap: spacing.sm,
  },
});
