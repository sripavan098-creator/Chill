import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Switch, View } from 'react-native';

import { Badge, InfoRow } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ConfirmModal } from '@/components/ui/Modal';
import { Screen } from '@/components/ui/Screen';
import { Body, Caption, Heading, Title } from '@/components/ui/TextBlock';
import { useSettings } from '@/features/settings/useSettings';
import { colors, spacing } from '@/theme';

export default function SettingsScreen() {
  const {
    voiceProfile,
    consent,
    appVersion,
    versionStatus,
    versionMessage,
    microphoneStatus,
    microphoneGranted,
    microphoneDenied,
    openMicrophoneSettings,
    simulateFailure,
    busy,
    error,
    deleteProfile,
    eraseAccount,
    revokeConsent,
    reset,
    setSimulateFailure,
  } = useSettings();

  const [confirmVisible, setConfirmVisible] = useState(false);
  const [accountConfirmVisible, setAccountConfirmVisible] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const onDelete = async () => {
    setMessage(null);
    const deleted = await deleteProfile();
    if (!deleted) return;
    setConfirmVisible(false);
    setMessage('Voice profile deleted. Raw audio was never stored.');
    router.replace('/welcome');
  };

  const onDeleteAccount = async () => {
    setMessage(null);
    const deleted = await eraseAccount();
    if (!deleted) return;
    setAccountConfirmVisible(false);
    router.replace('/welcome');
  };

  const onReset = async () => {
    await reset();
    router.replace('/welcome');
  };

  const onConsentAction = () => {
    if (consent?.granted) {
      void revokeConsent();
    } else {
      router.push('/consent');
    }
  };

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.header}>
        <Title>Settings</Title>
        <Body color={colors.textSecondary}>
          Manage your voice profile and privacy controls.
        </Body>
      </View>

      {message ? (
        <Card tone="success">
          <Caption color={colors.success}>{message}</Caption>
        </Card>
      ) : null}

      <Card>
        <View style={styles.cardHeader}>
          <Heading>Voice profile</Heading>
          <Badge
            label={voiceProfile ? 'Enrolled' : 'Not enrolled'}
            tone={voiceProfile ? 'success' : 'warning'}
          />
        </View>
        <InfoRow label="Owner name" value={voiceProfile?.displayName ?? '—'} />
        <InfoRow
          label="Phrases captured"
          value={voiceProfile ? `${voiceProfile.phraseCount} of 5` : '—'}
        />
        <InfoRow
          label="Profile created"
          value={
            voiceProfile ? new Date(voiceProfile.createdAt).toLocaleDateString() : '—'
          }
        />
        <InfoRow label="Raw audio stored" value="None" tone="success" />
      </Card>

      <Card>
        <View style={styles.cardHeader}>
          <Heading>Microphone</Heading>
          <Badge
            label={
              microphoneGranted
                ? 'Granted'
                : microphoneDenied
                  ? 'Denied'
                  : 'Not requested'
            }
            tone={microphoneGranted ? 'success' : microphoneDenied ? 'danger' : 'warning'}
          />
        </View>
        <Caption>
          Chill uses the microphone only to enroll and recognize your voice.
        </Caption>
        {microphoneDenied ? (
          <Button
            label="Open device settings"
            variant="secondary"
            onPress={openMicrophoneSettings}
            accessibilityHint="Open the device settings for Chill"
          />
        ) : null}
        <Caption color={colors.textSecondary}>{`Status: ${microphoneStatus}`}</Caption>
      </Card>

      <Card>
        <Heading>Consent</Heading>
        <InfoRow
          label="Voice processing"
          value={consent?.granted ? 'Granted' : 'Not granted'}
          tone={consent?.granted ? 'success' : 'danger'}
        />
        <InfoRow label="Policy version" value={consent?.policyVersion ?? '—'} />
        <InfoRow
          label="Granted on"
          value={
            consent?.grantedAt ? new Date(consent.grantedAt).toLocaleDateString() : '—'
          }
        />
        <Button
          label={consent?.granted ? 'Withdraw consent' : 'Grant consent'}
          variant="secondary"
          onPress={onConsentAction}
          accessibilityHint="Change your voice consent state"
        />
      </Card>

      <Card tone="danger">
        <Heading>Delete voice profile</Heading>
        <Caption>
          Removes the mock owner profile from this device. You will need to enroll again to
          sign in with voice.
        </Caption>
        <Button
          label="Delete voice profile"
          variant="danger"
          onPress={() => setConfirmVisible(true)}
          disabled={!voiceProfile}
          accessibilityHint="Open a confirmation dialog before deleting"
        />
      </Card>

      <Card tone="danger">
        <Heading>Delete account</Heading>
        <Caption>
          Removes everything: voice profile, consent, memories, and the device session. This
          cannot be undone.
        </Caption>
        <Button
          label="Delete account"
          variant="danger"
          onPress={() => setAccountConfirmVisible(true)}
          accessibilityHint="Open a confirmation dialog before deleting your account"
        />
      </Card>

      <Card>
        <Heading>Help and legal</Heading>
        <Caption>Send feedback about the beta, or read how Chill treats your voice.</Caption>
        <Button
          label="Send feedback"
          variant="secondary"
          onPress={() => router.push('/feedback')}
          accessibilityHint="Open the feedback screen"
        />
        <Button
          label="Privacy and terms"
          variant="secondary"
          onPress={() => router.push('/legal')}
          accessibilityHint="Open the privacy summary and document links"
        />
      </Card>

      <Card>
        <View style={styles.cardHeader}>
          <Heading>About</Heading>
          <Badge
            label={versionStatus === 'ok' ? 'Up to date' : 'Version'}
            tone={versionStatus === 'ok' ? 'success' : 'info'}
          />
        </View>
        <InfoRow label="App version" value={appVersion} />
        <InfoRow label="Backend check" value={versionStatus} />
        {versionMessage ? <Caption>{versionMessage}</Caption> : null}
      </Card>

      <Card>
        <View style={styles.cardHeader}>
          <Heading>Developer options</Heading>
          <Badge label="Mock" tone="warning" />
        </View>
        <Caption>Force the next mock verification to fail.</Caption>
        <View style={styles.switchRow}>
          <Body>Simulate verification failure</Body>
          <Switch
            value={simulateFailure}
            onValueChange={setSimulateFailure}
            trackColor={{ false: colors.border, true: colors.primary }}
            thumbColor={colors.card}
            accessibilityLabel="Simulate voice verification failure"
          />
        </View>
      </Card>

      {error ? <Caption color={colors.danger}>{error}</Caption> : null}

      <View style={styles.actions}>
        <Button
          label="Reset onboarding"
          variant="ghost"
          onPress={onReset}
          accessibilityHint="Clear all mock local state and restart onboarding"
        />
        <Button label="Back" variant="secondary" onPress={() => router.back()} />
      </View>

      <ConfirmModal
        visible={confirmVisible}
        title="Delete voice profile?"
        message="This removes your mock voice profile from this device. You can enroll again later."
        confirmLabel="Delete"
        destructive
        loading={busy}
        onConfirm={onDelete}
        onCancel={() => setConfirmVisible(false)}
      />

      <ConfirmModal
        visible={accountConfirmVisible}
        title="Delete account?"
        message="This removes your voice profile, consent, memories, and device session. This cannot be undone."
        confirmLabel="Delete account"
        destructive
        loading={busy}
        onConfirm={onDeleteAccount}
        onCancel={() => setAccountConfirmVisible(false)}
      />
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
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.sm,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
  },
  actions: {
    gap: spacing.sm,
  },
});
