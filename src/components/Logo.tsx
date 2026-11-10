import { StyleSheet, Text, View } from "react-native";

import { Fonts, Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { Icon } from "./Icon";

/** Double note on an orange square. */
export function LogoMark({ size = 52 }: { size?: number }) {
  const c = useTheme();
  return (
    <View
      accessible={false}
      style={[styles.mark, { width: size, height: size, borderRadius: size > 48 ? 16 : Radii.sm, backgroundColor: c.orange }]}
    >
      <Icon name="note" size={Math.round(size * 0.55)} color={c.onOrange} strokeWidth={2} />
    </View>
  );
}

export function Logo({ size = 44, color }: { size?: number; color?: string }) {
  const c = useTheme();
  return (
    <View style={styles.row} accessibilityRole="header">
      <LogoMark size={size} />
      <Text style={[styles.name, { color: color ?? c.ink }]}>MusicStudio</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  mark: { alignItems: "center", justifyContent: "center" },
  row: { flexDirection: "row", alignItems: "center", gap: 12 },
  name: { fontFamily: Fonts.display, fontSize: 24, letterSpacing: -0.24 },
});
