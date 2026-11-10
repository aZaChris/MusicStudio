import { ActivityIndicator, StyleSheet, Text, type PressableProps } from "react-native";

import { Fonts, Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { PressScale } from "./Motion";

type Variant = "primary" | "secondary" | "ghost" | "success";

interface ButtonProps extends Omit<PressableProps, "style" | "children"> {
  title: string;
  variant?: Variant;
  loading?: boolean;
  /** 54px tall, for the one main action of a form. */
  large?: boolean;
  /** Fill the width of the parent. */
  block?: boolean;
}

/** Pill button. Text on orange is always `onOrange`, never white (it would fail contrast). */
export function Button({ title, variant = "primary", loading, large, block, disabled, ...rest }: ButtonProps) {
  const c = useTheme();
  const palette = {
    primary: { bg: c.orange, fg: c.onOrange, border: "transparent" },
    secondary: { bg: "transparent", fg: c.ink, border: c.ink },
    ghost: { bg: "transparent", fg: c.orangeText, border: "transparent" },
    success: { bg: c.card, fg: c.okFg, border: c.teal },
  }[variant];
  const inactive = !!(disabled || loading);

  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled: inactive, busy: !!loading }}
      disabled={inactive}
      style={[
        styles.base,
        large && styles.large,
        block && styles.block,
        { backgroundColor: palette.bg, borderColor: palette.border, opacity: disabled ? 0.5 : 1 },
      ]}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={palette.fg} />
      ) : (
        <Text style={[styles.text, large && styles.textLarge, { color: palette.fg }]}>{title}</Text>
      )}
    </PressScale>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 48,
    paddingHorizontal: 22,
    borderRadius: Radii.pill,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 8,
  },
  large: { height: 54, paddingHorizontal: 26 },
  block: { alignSelf: "stretch" },
  text: { fontFamily: Fonts.bodyBold, fontSize: 16 },
  textLarge: { fontSize: 17 },
});
