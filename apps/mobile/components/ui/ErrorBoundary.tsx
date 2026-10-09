import { Component, ErrorInfo, PropsWithChildren, ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Body, Caption, Title } from '@/components/ui/TextBlock';
import { colors, spacing } from '@/theme';

interface ErrorBoundaryProps {
  /** Rendered when a child throws. Receives a reset callback. */
  fallback?: (reset: () => void) => ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches render errors so a single broken screen does not take down the app.
 *
 * The default fallback is deliberately calm and offers a way out: retry (reset
 * the boundary) or note that the user's data is safe. It never shows a stack
 * trace, since those can leak internals into a screenshot.
 */
export class ErrorBoundary extends Component<
  PropsWithChildren<ErrorBoundaryProps>,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    this.props.onError?.(error, info);
  }

  reset = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (!this.state.error) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback(this.reset);
    }

    return (
      <View style={styles.root}>
        <Card>
          <Title>Something went wrong</Title>
          <Body color={colors.textSecondary}>
            Chill hit an unexpected problem on this screen. Your voice profile and
            settings are safe.
          </Body>
          <Caption color={colors.textSecondary}>
            If it keeps happening, restart the app or send feedback from Settings.
          </Caption>
          <Button
            label="Try again"
            onPress={this.reset}
            accessibilityHint="Reload the screen that failed"
          />
        </Card>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing.lg,
    backgroundColor: colors.background,
  },
});
