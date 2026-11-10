import { StyleSheet, Text, View } from "react-native";

import { Fonts, Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import type { LessonStatus, PaymentStatus } from "@/lib/api/types";

export type Tone = "ok" | "wait" | "bad" | "plan" | "off" | "low";

/** The state is always in the text: colour alone never carries it. */
export function StatusChip({ tone, label, small }: { tone: Tone; label: string; small?: boolean }) {
  const c = useTheme();
  const palette = {
    ok: [c.okBg, c.okFg],
    wait: [c.waitBg, c.waitFg],
    bad: [c.badBg, c.badFg],
    plan: [c.planBg, c.planFg],
    off: [c.offBg, c.offFg],
    // orange-text on orange-soft is 4.16:1; ink passes comfortably (docs/design-system.md)
    low: [c.orangeSoft, c.ink],
  }[tone];
  return (
    <View style={[styles.base, small && styles.small, { backgroundColor: palette[0] }]}>
      <Text style={[styles.text, small && styles.textSmall, { color: palette[1] }]}>{label}</Text>
    </View>
  );
}

export const paymentTone = (s: PaymentStatus | string | null | undefined): Tone =>
  s === "paid" ? "ok" : s === "overdue" ? "bad" : "wait";
export const lessonTone = (s: LessonStatus): Tone => (s === "completed" ? "ok" : s === "scheduled" ? "plan" : "off");
export const packageTone = (s: string): Tone => (s === "active" ? "ok" : s === "expired" ? "bad" : "off");

const styles = StyleSheet.create({
  base: { alignSelf: "flex-start", borderRadius: Radii.pill, paddingHorizontal: 12, paddingVertical: 6 },
  small: { paddingHorizontal: 10, paddingVertical: 3 },
  text: { fontFamily: Fonts.bodyBold, fontSize: 13 },
  textSmall: { fontSize: 12 },
});
