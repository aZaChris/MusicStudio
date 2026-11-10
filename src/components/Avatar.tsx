import { StyleSheet, Text, View } from "react-native";

import { Fonts } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";

/** Initials on a rounded square. The colour follows the position in the list. */
export function Avatar({ name, index = 0, size = 52, circle }: { name: string; index?: number; size?: number; circle?: boolean }) {
  const c = useTheme();
  const tints = [
    [c.avatarPlum, "#fbf5ec"],
    [c.avatarOrange, "#2b1d14"],
    [c.avatarTeal, "#ffffff"],
    [c.avatarPeach, "#2b1d14"],
    [c.avatarLilac, "#fbf5ec"],
  ] as const;
  const [bg, fg] = tints[index % tints.length];
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
  return (
    <View
      accessible={false}
      importantForAccessibility="no-hide-descendants"
      style={[styles.base, { width: size, height: size, borderRadius: circle ? size / 2 : Math.round(size * 0.31), backgroundColor: bg }]}
    >
      <Text style={{ fontFamily: Fonts.display, fontSize: Math.round(size * 0.35), color: fg }}>{initials}</Text>
    </View>
  );
}

const styles = StyleSheet.create({ base: { alignItems: "center", justifyContent: "center" } });
