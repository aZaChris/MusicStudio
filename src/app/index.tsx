import { Redirect } from "expo-router";
import { StyleSheet, View } from "react-native";

import { Alert } from "@/components/Alert";
import { Button } from "@/components/Button";
import { LogoMark } from "@/components/Logo";
import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";

export default function Index() {
  const { user, status, retry } = useAuth();
  const c = useTheme();
  const t = useT();

  if (status === "loading") {
    return (
      <View style={[styles.center, { backgroundColor: c.paper }]} accessibilityLabel={t("common.loading")}>
        <LogoMark size={64} />
      </View>
    );
  }
  if (status === "unreachable") {
    // A session is stored but cannot be confirmed: do not guess the role, do not sign out.
    return (
      <View style={[styles.center, { backgroundColor: c.paper }]}>
        <Alert kind="warning">{t("auth.unreachable")}</Alert>
        <Button title={t("common.retry")} onPress={retry} />
      </View>
    );
  }
  if (!user) return <Redirect href="/login" />;
  if (user.role === "parent" || user.role === "student") return <Redirect href="/(parent)/portal" />;
  return <Redirect href="/(teacher)/home" />;
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 16, padding: 24 },
});
