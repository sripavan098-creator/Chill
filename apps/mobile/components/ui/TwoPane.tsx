import { PropsWithChildren, ReactNode } from 'react';
import { StyleSheet, useWindowDimensions, View } from 'react-native';

import { spacing } from '@/theme';

export const WIDE_BREAKPOINT = 900;

interface TwoPaneProps {
  /** Receives true on laptop-width windows so the visual can scale up. */
  visual: (wide: boolean) => ReactNode;
}

export function TwoPane({ visual, children }: PropsWithChildren<TwoPaneProps>) {
  const { width } = useWindowDimensions();
  const wide = width >= WIDE_BREAKPOINT;
  return (
    <View style={[styles.root, wide && styles.row]}>
      <View style={[styles.visual, wide && styles.visualWide]}>{visual(wide)}</View>
      <View style={[styles.body, wide && styles.bodyWide]}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { gap: spacing.lg, width: '100%' },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.xxl },
  visual: { alignItems: 'center' },
  visualWide: { flex: 1 },
  body: { gap: spacing.lg },
  bodyWide: { flex: 1, maxWidth: 520 },
});
