import { StyleSheet, View, type ViewProps } from "react-native";

import { Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";

/** Flat card: 1px line, no shadow (shadows are for what floats). `row` uses the smaller radius. */
export function Card({ style, row, ...rest }: ViewProps & { row?: boolean }) {
  const c = useTheme();
  return (
    <View
      style={[
        styles.base,
        { backgroundColor: c.card, borderColor: c.line, borderRadius: row ? Radii.row : Radii.card, padding: row ? 14 : 20 },
        style,
      ]}
      {...rest}
    />
  );
}

const styles = StyleSheet.create({ base: { borderWidth: 1 } });
