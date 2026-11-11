import { Redirect, Tabs } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { Icon, type IconName } from "@/components/Icon";
import { Fonts, Radii } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";

// The active tab gets a soft orange pill behind its icon (design: bottom bar).
function TabIcon({ name, focused }: { name: IconName; focused: boolean }) {
  const c = useTheme();
  return (
    <View style={[styles.pill, focused && { backgroundColor: c.orangeSoft }]}>
      <Icon name={name} size={20} color={focused ? c.orangeText : c.ink2} />
    </View>
  );
}

function TabLabel({ title, focused }: { title: string; focused: boolean }) {
  const c = useTheme();
  return <Text style={[styles.label, { color: focused ? c.ink : c.ink2, fontFamily: focused ? Fonts.bodyBold : Fonts.bodySemi }]}>{title}</Text>;
}

export default function TeacherLayout() {
  const { user, status } = useAuth();
  const c = useTheme();
  const t = useT();

  if (status === "loading") return null;
  if (!user) return <Redirect href="/login" />;
  if (user.role === "parent" || user.role === "student") return <Redirect href="/(parent)/portal" />;

  const tab = (title: string, icon: IconName) => ({
    title,
    tabBarIcon: ({ focused }: { focused: boolean }) => <TabIcon name={icon} focused={focused} />,
    tabBarLabel: ({ focused }: { focused: boolean }) => <TabLabel title={title} focused={focused} />,
  });

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: { backgroundColor: c.card, borderTopColor: c.line, borderTopWidth: 1, paddingTop: 10 },
        tabBarItemStyle: { gap: 4 },
      }}
    >
      <Tabs.Screen name="home" options={tab(t("nav.home"), "home")} />
      <Tabs.Screen name="roster" options={tab(t("nav.students"), "students")} />
      <Tabs.Screen name="payments" options={tab(t("nav.payments"), "payments")} />
      <Tabs.Screen name="account" options={tab(t("nav.account"), "check")} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  pill: { width: 56, height: 30, borderRadius: Radii.pill, alignItems: "center", justifyContent: "center" },
  label: { fontSize: 12 },
});
