import { Stack } from "expo-router";

import { LogoutButton } from "@/components/LogoutButton";

import { Fonts } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useT } from "@/lib/i18n";

export default function RosterLayout() {
  const theme = useTheme();
  const t = useT();
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: theme.backgroundElement },
        headerTintColor: theme.text,
        headerTitleStyle: { fontFamily: Fonts.heading },
      }}
    >
      <Stack.Screen name="index" options={{ title: t("roster.title"), headerRight: () => <LogoutButton /> }} />
      <Stack.Screen name="[id]" options={{ title: "" }} />
    </Stack>
  );
}
