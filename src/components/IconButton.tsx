import { StyleSheet } from "react-native";

import { useTheme } from "@/hooks/use-theme";
import { Icon, type IconName } from "./Icon";
import { PressScale } from "./Motion";

/** 44px round icon button. Icon-only, so the label is required: it is the accessible name. */
export function IconButton({
  icon,
  label,
  onPress,
  tone = "plain",
}: {
  icon: IconName;
  label: string;
  onPress: () => void;
  tone?: "plain" | "success" | "accent";
}) {
  const c = useTheme();
  const palette = {
    plain: { bg: c.card, fg: c.ink, border: c.line },
    success: { bg: c.card, fg: c.okFg, border: c.teal },
    accent: { bg: c.orange, fg: c.onOrange, border: "transparent" },
  }[tone];
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      to={0.94}
      style={[styles.base, { backgroundColor: palette.bg, borderColor: palette.border }]}
    >
      <Icon name={icon} color={palette.fg} strokeWidth={tone === "success" ? 2.4 : 2} />
    </PressScale>
  );
}

const styles = StyleSheet.create({
  base: { width: 44, height: 44, borderRadius: 22, borderWidth: 1.5, alignItems: "center", justifyContent: "center" },
});
