import { Pressable, Text } from "react-native";

import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";

/** Header action available to every role (audit issue 4). */
export function LogoutButton() {
  const { logout } = useAuth();
  const theme = useTheme();
  const t = useT();
  return (
    <Pressable
      onPress={logout}
      hitSlop={12}
      accessibilityRole="button"
      accessibilityLabel={t("auth.logout")}
      style={{ marginHorizontal: 16 }}
    >
      <Text style={{ color: theme.accent, fontSize: 14 }}>{t("auth.logout")}</Text>
    </Pressable>
  );
}
