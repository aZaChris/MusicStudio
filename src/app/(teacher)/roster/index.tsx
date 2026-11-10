import { useRouter } from "expo-router";
import { useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Avatar } from "@/components/Avatar";
import { Beats } from "@/components/Beats";
import { Card } from "@/components/Card";
import { Icon } from "@/components/Icon";
import { PressScale } from "@/components/Motion";
import { QueryState } from "@/components/QueryState";
import { ScreenHeader } from "@/components/Screen";
import { paymentTone, StatusChip } from "@/components/StatusChip";
import { Fonts, Radii, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { enumLabel, paymentStatusKey, useT } from "@/lib/i18n";
import type { PaymentStatus } from "@/lib/api/types";
import { useStudents } from "@/lib/queries";

export default function RosterScreen() {
  const c = useTheme();
  const t = useT();
  const router = useRouter();
  const students = useStudents();
  const list = students.data ?? [];
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();
  const shown = needle ? list.filter((s) => `${s.full_name} ${s.instrument}`.toLowerCase().includes(needle)) : list;

  // Loading, error and empty keep the page title; the list view carries its own as a header.
  if (students.isPending || students.isError || list.length === 0) {
    return (
      <SafeAreaView style={[styles.fill, { backgroundColor: c.paper }]} edges={["top"]}>
        <View style={styles.list}>
          <ScreenHeader title={t("roster.title")} />
          <View style={{ height: 16 }} />
          <QueryState query={students} isEmpty emptyText={t("roster.empty")}>
            {null}
          </QueryState>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.fill, { backgroundColor: c.paper }]} edges={["top"]}>
      <QueryState query={students} isEmpty={list.length === 0} emptyText={t("roster.empty")}>
        <FlatList
          testID="roster-list"
          data={shown}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.list}
          keyboardShouldPersistTaps="handled"
          refreshControl={<RefreshControl refreshing={students.isRefetching} onRefresh={students.refetch} />}
          ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
          ListHeaderComponent={
            <View style={styles.head}>
              <ScreenHeader title={t("roster.title")} eyebrow={t("roster.activeCount", { count: String(list.length) })} />
              <View style={[styles.search, { backgroundColor: c.card, borderColor: c.line }]}>
                <Icon name="search" size={18} color={c.ink2} strokeWidth={2} />
                <TextInput
                  accessibilityLabel={t("roster.search")}
                  placeholder={t("roster.searchPlaceholder")}
                  placeholderTextColor={c.ink2}
                  value={query}
                  onChangeText={setQuery}
                  style={[styles.searchInput, { color: c.ink }]}
                />
              </View>
            </View>
          }
          ListEmptyComponent={<Text style={[Type.small, { color: c.ink2 }]}>{t("roster.noMatch")}</Text>}
          renderItem={({ item, index }) => {
            const pkg = item.active_package;
            return (
              <PressScale
                accessibilityRole="button"
                accessibilityLabel={item.full_name}
                onPress={() => router.push(`/(teacher)/roster/${item.id}`)}
                to={0.98}
              >
                <Card row style={styles.row}>
                  <Avatar name={item.full_name} index={index} size={48} />
                  <View style={styles.rowText}>
                    <View style={styles.nameLine}>
                      <Text numberOfLines={1} style={[Type.bodyStrong, styles.name, { color: c.ink }]}>
                        {item.full_name}
                      </Text>
                      {pkg?.is_low && <StatusChip tone="low" small label={t("roster.lowPackage")} />}
                    </View>
                    <Text style={[Type.small, { color: c.ink2 }]}>{item.instrument}</Text>
                    {pkg ? (
                      <View style={styles.beatLine}>
                        <Beats size="s" total={pkg.total_lessons} used={pkg.total_lessons - pkg.lessons_remaining} />
                        <Text style={[styles.remaining, { color: c.ink2 }]}>{t("roster.remainingCount", { count: String(pkg.lessons_remaining) })}</Text>
                      </View>
                    ) : (
                      <Text style={[styles.remaining, { color: c.ink2 }]}>{t("roster.noPackage")}</Text>
                    )}
                    {item.payment_status && (
                      <StatusChip tone={paymentTone(item.payment_status)} small label={enumLabel(t, paymentStatusKey(item.payment_status as PaymentStatus))} />
                    )}
                  </View>
                </Card>
              </PressScale>
            );
          }}
        />
      </QueryState>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  list: { paddingHorizontal: 20, paddingTop: 12, paddingBottom: 32 },
  head: { gap: 16, paddingBottom: 16 },
  search: { flexDirection: "row", alignItems: "center", gap: 10, height: 48, paddingHorizontal: 16, borderRadius: Radii.pill, borderWidth: 1.5 },
  searchInput: { flex: 1, fontFamily: Fonts.body, fontSize: 16, height: 48 },
  row: { flexDirection: "row", alignItems: "center", gap: 14 },
  rowText: { flex: 1, gap: 6, alignItems: "flex-start" },
  nameLine: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, alignSelf: "stretch" },
  name: { flexShrink: 1 },
  beatLine: { flexDirection: "row", alignItems: "center", gap: 8 },
  remaining: { fontFamily: Fonts.bodyBold, fontSize: 12 },
});
