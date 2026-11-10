import { useState } from "react";
import { StyleSheet, Text, TextInput, View, type TextInputProps } from "react-native";

import { Fonts, Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";

export function TextField({
  label,
  invalid,
  style,
  multiline,
  onFocus,
  onBlur,
  ...rest
}: TextInputProps & { label: string; invalid?: boolean }) {
  const c = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.wrapper}>
      <Text style={[styles.label, { color: c.ink }]}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={c.ink2}
        multiline={multiline}
        onFocus={(e) => {
          setFocused(true);
          onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          onBlur?.(e);
        }}
        style={[
          styles.input,
          multiline && styles.multiline,
          {
            color: c.ink,
            backgroundColor: c.card,
            // Active field: orange border (design/system README); error: bad-fg.
            borderColor: invalid ? c.badFg : focused ? c.orange : c.line,
          },
          style,
        ]}
        {...rest}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: 6 },
  label: { fontFamily: Fonts.bodyBold, fontSize: 13 },
  input: {
    height: 52,
    fontFamily: Fonts.body,
    fontSize: 16,
    borderWidth: 1.5,
    borderRadius: Radii.field,
    paddingHorizontal: 16,
  },
  multiline: { height: undefined, minHeight: 92, paddingTop: 12, paddingBottom: 12, textAlignVertical: "top" },
});
