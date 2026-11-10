import { StyleSheet, Text } from "react-native";

import { Fonts, Radii, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { PressScale } from "./Motion";

/** A big number with a label: plum for the main one, orange for what needs action, card for the rest. */
export function StatCard({
  value,
  label,
  tone,
  onPress,
}: {
  value: number | string;
  label: string;
  tone: "plum" | "orange" | "card";
  onPress?: () => void;
}) {
  const c = useTheme();
  const palette = {
    plum: { bg: c.plum, figure: c.onPlum, label: c.plumSoft, border: "transparent" },
    orange: { bg: c.orange, figure: c.onOrange, label: c.onOrange, border: "transparent" },
    card: { bg: c.card, figure: c.orangeText, label: c.ink2, border: c.line },
  }[tone];
  return (
    <PressScale
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? "link" : undefined}
      accessibilityLabel={`${value} ${label}`}
      style={[styles.card, { backgroundColor: palette.bg, borderColor: palette.border }]}
    >
      <Text style={[Type.number, { color: palette.figure }]}>{value}</Text>
      <Text style={[styles.label, { color: palette.label }, tone === "orange" && { fontFamily: Fonts.bodyBold }]}>{label}</Text>
    </PressScale>
  );
}

const styles = StyleSheet.create({
  card: { flex: 1, minHeight: 120, borderRadius: Radii.card, borderWidth: 1, padding: 18, gap: 4 },
  label: { fontFamily: Fonts.bodySemi, fontSize: 15 },
});
