import { StyleSheet, Text, TextInput, View, type TextInputProps } from "react-native";

import { Fonts, Radius, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";

export function TextField({ label, style, ...rest }: TextInputProps & { label: string }) {
  const theme = useTheme();
  return (
    <View style={styles.wrapper}>
      <Text style={[styles.label, { color: theme.textSecondary }]}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={theme.textSecondary}
        style={[
          styles.input,
          { color: theme.text, borderColor: theme.border, backgroundColor: theme.backgroundElement },
          style,
        ]}
        {...rest}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: Spacing.one },
  label: { fontFamily: Fonts.bodyBold, fontSize: 13 },
  input: {
    fontFamily: Fonts.body,
    fontSize: 15,
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingVertical: Spacing.two + 2,
    paddingHorizontal: Spacing.three,
  },
});
