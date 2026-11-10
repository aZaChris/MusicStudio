import type { ReactNode } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View, type RefreshControlProps } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";

/** Warm paper background, 20px side margin, scrolls. `refreshControl` adds pull-to-refresh. */
export function Screen({
  children,
  refreshControl,
  edges = ["top"],
  padBottom = true,
}: {
  children: ReactNode;
  refreshControl?: RefreshControlProps;
  edges?: ("top" | "bottom")[];
  padBottom?: boolean;
}) {
  const c = useTheme();
  return (
    <SafeAreaView style={[styles.fill, { backgroundColor: c.paper }]} edges={edges}>
      <ScrollView
        contentContainerStyle={[styles.content, padBottom && styles.bottom]}
        refreshControl={refreshControl ? <RefreshControl {...refreshControl} /> : undefined}
        keyboardShouldPersistTaps="handled"
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

/** Large page title with an optional small line above it and an action on the right. */
export function ScreenHeader({ title, eyebrow, right }: { title: string; eyebrow?: string; right?: ReactNode }) {
  const c = useTheme();
  return (
    <View style={styles.header}>
      <View style={styles.headerText}>
        {eyebrow ? <Text style={[Type.small, { color: c.ink2 }]}>{eyebrow}</Text> : null}
        <Text accessibilityRole="header" style={[Type.title, { color: c.ink }]}>
          {title}
        </Text>
      </View>
      {right}
    </View>
  );
}

export function SectionTitle({ children }: { children: string }) {
  const c = useTheme();
  return (
    <Text accessibilityRole="header" style={[Type.heading, { color: c.ink }]}>
      {children}
    </Text>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  content: { paddingHorizontal: 20, paddingTop: 12, gap: 16 },
  bottom: { paddingBottom: 32 },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 },
  headerText: { flex: 1, gap: 2 },
});
