import { Redirect, Stack } from "expo-router";

import { Fonts } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";

export default function ParentLayout() {
  const { user, isLoading } = useAuth();
  const theme = useTheme();

  if (isLoading) return null;
  if (!user) return <Redirect href="/login" />;
  if (user.role !== "parent") return <Redirect href="/(teacher)/home" />;

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: theme.backgroundElement },
        headerTintColor: theme.text,
        headerTitleStyle: { fontFamily: Fonts.heading },
      }}
    />
  );
}
