import { useRouter } from "expo-router";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "@/components/Card";
import { QueryState } from "@/components/QueryState";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { enumLabel, paymentStatusKey, useT } from "@/lib/i18n";
import type { PaymentStatus } from "@/lib/api/types";
import { useStudents } from "@/lib/queries";

export default function RosterScreen() {
  const theme = useTheme();
  const t = useT();
  const router = useRouter();
  const students = useStudents();
  const list = students.data ?? [];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <QueryState query={students} isEmpty={list.length === 0} emptyText={t("roster.empty")}>
        <FlatList
          testID="roster-list"
          data={list}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={students.isRefetching} onRefresh={students.refetch} />}
          ItemSeparatorComponent={() => <View style={{ height: Spacing.two }} />}
          renderItem={({ item }) => {
            const pkg = item.active_package;
            return (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={item.full_name}
                onPress={() => router.push(`/(teacher)/roster/${item.id}`)}
              >
                <Card style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontFamily: Fonts.bodyBold, fontSize: 15, color: theme.text }}>
                      {item.full_name}
                    </Text>
                    <Text style={{ fontSize: 12.5, color: theme.textSecondary }}>{item.instrument}</Text>
                  </View>
                  <View style={{ alignItems: "flex-end", gap: 4 }}>
                    {pkg && (
                      <Text style={{ fontSize: 12.5, color: theme.textSecondary }}>
                        {pkg.lessons_remaining}/{pkg.total_lessons} {t("roster.remaining")}
                      </Text>
                    )}
                    {pkg?.is_low && (
                      <View style={[styles.badge, { backgroundColor: theme.warningBg }]}>
                        <Text style={{ fontSize: 11, color: theme.warningText }}>{t("roster.lowPackage")}</Text>
                      </View>
                    )}
                    {item.payment_status && (
                      <Text style={{ fontSize: 11.5, color: theme.textSecondary }}>
                        {enumLabel(t, paymentStatusKey(item.payment_status as PaymentStatus))}
                      </Text>
                    )}
                  </View>
                </Card>
              </Pressable>
            );
          }}
        />
      </QueryState>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  list: { padding: Spacing.three },
  row: { flexDirection: "row", alignItems: "center", gap: Spacing.two },
  badge: { borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2 },
});
