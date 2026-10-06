import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { ChillProvider } from '@/state/ChillContext';
import { colors } from '@/theme';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ChillProvider>
        <StatusBar style="dark" />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.background },
            animation: 'slide_from_right',
          }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="welcome" />
          <Stack.Screen name="permissions" />
          <Stack.Screen name="consent" />
          <Stack.Screen name="enroll" />
          <Stack.Screen name="enroll-success" options={{ gestureEnabled: false }} />
          <Stack.Screen name="login" />
          <Stack.Screen name="fallback" />
          <Stack.Screen name="home" />
          <Stack.Screen name="settings" />
        </Stack>
      </ChillProvider>
    </SafeAreaProvider>
  );
}
