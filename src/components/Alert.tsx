import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Fonts, Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { Icon } from "./Icon";

type Kind = "error" | "warning" | "success" | "info" | "package";

/** Message box with an icon. `package` is the orange "running low" notice. */
export function Alert({ kind, children, live = true }: { kind: Kind; children: ReactNode; live?: boolean }) {
  const c = useTheme();
  const palette = {
    error: [c.badBg, c.badFg, "transparent"],
    warning: [c.waitBg, c.waitFg, "transparent"],
    success: [c.okBg, c.okFg, "transparent"],
    info: [c.planBg, c.planFg, "transparent"],
    package: [c.orangeSoft, c.ink, c.orangeBorder],
  }[kind];
  return (
    <View
      accessibilityRole={live ? "alert" : undefined}
      style={[styles.box, kind === "package" && styles.pkg, { backgroundColor: palette[0], borderColor: palette[2] }]}
    >
      <Icon name={kind === "success" ? "check" : "alert"} size={kind === "package" ? 22 : 18} color={kind === "package" ? c.orangeText : palette[1]} />
      <Text style={[styles.text, { color: palette[1] }]}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: { flexDirection: "row", gap: 10, alignItems: "flex-start", paddingVertical: 12, paddingHorizontal: 14, borderRadius: Radii.field, borderWidth: 1.5 },
  pkg: { alignItems: "center", borderRadius: 18, paddingVertical: 14, paddingHorizontal: 16 },
  text: { flex: 1, fontFamily: Fonts.bodySemi, fontSize: 14, lineHeight: 20 },
});
