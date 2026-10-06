import { PropsWithChildren } from 'react';
import { StyleSheet, Text, TextProps } from 'react-native';

import { colors, typography } from '@/theme';

type Variant = 'title' | 'heading' | 'body' | 'bodyStrong' | 'caption';

interface TextBlockProps extends TextProps {
  variant?: Variant;
  color?: string;
  center?: boolean;
}

export function TextBlock({
  children,
  variant = 'body',
  color,
  center,
  style,
  ...rest
}: PropsWithChildren<TextBlockProps>) {
  return (
    <Text
      style={[
        typography[variant],
        color ? { color } : null,
        center ? styles.center : null,
        style,
      ]}
      {...rest}>
      {children}
    </Text>
  );
}

export function Title(props: PropsWithChildren<Omit<TextBlockProps, 'variant'>>) {
  return <TextBlock variant="title" {...props} />;
}

export function Heading(props: PropsWithChildren<Omit<TextBlockProps, 'variant'>>) {
  return <TextBlock variant="heading" {...props} />;
}

export function Body(props: PropsWithChildren<Omit<TextBlockProps, 'variant'>>) {
  return <TextBlock variant="body" {...props} />;
}

export function Caption(props: PropsWithChildren<Omit<TextBlockProps, 'variant'>>) {
  return <TextBlock variant="caption" color={colors.textSecondary} {...props} />;
}

const styles = StyleSheet.create({
  center: {
    textAlign: 'center',
  },
});
