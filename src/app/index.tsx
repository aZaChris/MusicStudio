import { Redirect } from "expo-router";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";

export default function Index() {
  const { user, status, retry } = useAuth();
  const theme = useTheme();
  const t = useT();

  if (status === "loading") {
    return (
      <View style={styles.center} accessibilityLabel={t("common.loading")}>
        <ActivityIndicator />
      </View>
    );
  }
  if (status === "unreachable") {
    // A session is stored but cannot be confirmed: do not guess the role, do not sign out.
    return (
      <View style={[styles.center, { backgroundColor: theme.background }]}>
        <Text accessibilityRole="alert" style={{ color: theme.text, textAlign: "center" }}>
          {t("auth.unreachable")}
        </Text>
        <Button title={t("common.retry")} onPress={retry} />
      </View>
    );
  }
  if (!user) return <Redirect href="/login" />;
  if (user.role === "parent") return <Redirect href="/(parent)/portal" />;
  return <Redirect href="/(teacher)/home" />;
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: Spacing.three, padding: Spacing.four },
});
