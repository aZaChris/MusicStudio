import { ActivityIndicator, Pressable, StyleSheet, Text, type PressableProps } from "react-native";

import { Colors, Fonts, Radius, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";

interface ButtonProps extends PressableProps {
  title: string;
  variant?: "primary" | "secondary";
  loading?: boolean;
}

export function Button({ title, variant = "primary", loading, disabled, style, ...rest }: ButtonProps) {
  const theme = useTheme();
  const isPrimary = variant === "primary";

  return (
    <Pressable
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.base,
        {
          backgroundColor: isPrimary ? Colors.light.accent : theme.backgroundElement,
          borderColor: isPrimary ? Colors.light.accent : theme.border,
          opacity: pressed || disabled ? 0.7 : 1,
        },
        typeof style === "function" ? undefined : style,
      ]}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={isPrimary ? "white" : theme.text} />
      ) : (
        <Text style={[styles.text, { color: isPrimary ? "white" : theme.text }]}>{title}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: Radius.sm,
    borderWidth: 1,
    paddingVertical: Spacing.three,
    paddingHorizontal: Spacing.four,
    alignItems: "center",
    justifyContent: "center",
  },
  text: {
    fontFamily: Fonts.bodyBold,
    fontSize: 15,
  },
});
