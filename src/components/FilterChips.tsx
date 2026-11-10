import { ScrollView, StyleSheet, Text, View } from "react-native";

import { Fonts, Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { PressScale } from "./Motion";

export interface ChipOption<T extends string | number> {
  id: T;
  label: string;
}

/**
 * Pill choices. `role` says what they mean: a filter (button, pressed), one of several
 * radio options, or a tab. Selected = filled ink (or orange with `accent`).
 */
export function FilterChips<T extends string | number>({
  options,
  value,
  onChange,
  role = "button",
  accent,
  scroll,
}: {
  options: ChipOption<T>[];
  value: T | null;
  onChange: (id: T) => void;
  role?: "button" | "radio" | "tab";
  accent?: boolean;
  /** One horizontal row that scrolls, for long lists (days, times). */
  scroll?: boolean;
}) {
  const c = useTheme();
  const Wrapper = scroll ? ScrollView : View;
  const wrapperProps = scroll
    ? { horizontal: true, showsHorizontalScrollIndicator: false, contentContainerStyle: styles.scrollRow, keyboardShouldPersistTaps: "handled" as const }
    : { style: styles.row };
  return (
    <Wrapper {...wrapperProps} accessibilityRole={role === "radio" ? "radiogroup" : role === "tab" ? "tablist" : undefined}>
      {options.map((o) => {
        const selected = value === o.id;
        const fill = accent ? c.orange : c.ink;
        const fg = accent ? c.onOrange : c.paper;
        return (
          <PressScale
            key={String(o.id)}
            onPress={() => onChange(o.id)}
            accessibilityRole={role}
            accessibilityLabel={o.label}
            accessibilityState={role === "button" ? { selected } : { selected }}
            style={[styles.chip, { backgroundColor: selected ? fill : c.card, borderColor: selected ? fill : c.line }]}
          >
            <Text style={[styles.text, { color: selected ? fg : c.ink }]}>{o.label}</Text>
          </PressScale>
        );
      })}
    </Wrapper>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  scrollRow: { flexDirection: "row", gap: 8, paddingRight: 8 },
  chip: { height: 40, paddingHorizontal: 16, borderRadius: Radii.pill, borderWidth: 1.5, justifyContent: "center" },
  text: { fontFamily: Fonts.bodyBold, fontSize: 14 },
});
