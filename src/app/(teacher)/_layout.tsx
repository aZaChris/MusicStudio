import { Redirect, Tabs } from "expo-router";
import { Text, type ColorValue } from "react-native";

import { LogoutButton } from "@/components/LogoutButton";

import { Fonts } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";

// Text glyphs as icons (no icon font added: parity). Hidden from screen readers: the tab
// title already says what it is.
function TabIcon({ symbol, color }: { symbol: string; color: ColorValue }) {
  return (
    <Text importantForAccessibility="no" accessibilityElementsHidden style={{ fontSize: 18, color }}>
      {symbol}
    </Text>
  );
}

export default function TeacherLayout() {
  const { user, status } = useAuth();
  const theme = useTheme();
  const t = useT();

  if (status === "loading") return null;
  if (!user) return <Redirect href="/login" />;
  if (user.role === "parent") return <Redirect href="/(parent)/portal" />;

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: theme.backgroundElement },
        headerTintColor: theme.text,
        headerTitleStyle: { fontFamily: Fonts.heading },
        tabBarActiveTintColor: theme.accent,
        tabBarInactiveTintColor: theme.textSecondary,
        tabBarStyle: { backgroundColor: theme.backgroundElement, borderTopColor: theme.border },
        // Teachers could not log out in the inherited app (audit issue 4).
        headerRight: () => <LogoutButton />,
      }}
    >
      <Tabs.Screen
        name="home"
        options={{ title: t("nav.home"), tabBarIcon: ({ color }) => <TabIcon symbol="⌂" color={color} /> }}
      />
      <Tabs.Screen
        name="roster"
        options={{
          title: t("nav.students"),
          headerShown: false, // roster/_layout.tsx's own Stack renders the header instead
          tabBarIcon: ({ color }) => <TabIcon symbol="☰" color={color} />,
        }}
      />
      <Tabs.Screen
        name="payments"
        options={{ title: t("nav.payments"), tabBarIcon: ({ color }) => <TabIcon symbol="€" color={color} /> }}
      />
    </Tabs>
  );
}
