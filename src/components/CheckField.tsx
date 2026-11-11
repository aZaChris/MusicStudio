import { Pressable, StyleSheet, Text, View } from "react-native";

import { Radii, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { Icon } from "./Icon";

/** A labelled checkbox (consent, "I understand"). */
export function CheckField({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  const c = useTheme();
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityLabel={label}
      accessibilityState={{ checked: value }}
      onPress={() => onChange(!value)}
      style={styles.row}
    >
      <View style={[styles.box, { borderColor: c.ink, backgroundColor: value ? c.orange : "transparent" }]}>
        {value ? <Icon name="check" size={16} color={c.onOrange} /> : null}
      </View>
      <Text style={[Type.body, styles.label, { color: c.ink }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 12, minHeight: 44 },
  box: { width: 24, height: 24, borderRadius: Radii.row / 2, borderWidth: 2, alignItems: "center", justifyContent: "center" },
  label: { flex: 1 },
});
