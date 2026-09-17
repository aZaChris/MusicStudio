import { useRouter } from "expo-router";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "@/components/Card";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useT, type TranslationKey } from "@/lib/i18n";
import { useStudents } from "@/lib/queries";

function statusKey(status: string): TranslationKey {
  return `payments.status${status.charAt(0).toUpperCase()}${status.slice(1)}` as TranslationKey;
}

export default function RosterScreen() {
  const theme = useTheme();
  const t = useT();
  const router = useRouter();
  const { data, isLoading, refetch, isRefetching } = useStudents();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <FlatList
        data={data?.results ?? []}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={isRefetching && !isLoading} onRefresh={refetch} />}
        ItemSeparatorComponent={() => <View style={{ height: Spacing.two }} />}
        renderItem={({ item }) => (
          <Pressable onPress={() => router.push(`/(teacher)/roster/${item.id}`)}>
            <Card style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={{ fontFamily: Fonts.bodyBold, fontSize: 15, color: theme.text }}>{item.fullName}</Text>
                <Text style={{ fontSize: 12.5, color: theme.textSecondary }}>{item.instrument}</Text>
              </View>
              <View style={{ alignItems: "flex-end", gap: 4 }}>
                {item.activePackage && (
                  <Text style={{ fontSize: 12.5, color: theme.textSecondary }}>
                    {item.activePackage.lessonsRemaining}/{item.activePackage.totalLessons} {t("roster.remaining")}
                  </Text>
                )}
                {item.activePackage?.isLow && (
                  <View style={[styles.badge, { backgroundColor: theme.warningBg }]}>
                    <Text style={{ fontSize: 11, color: theme.warningText }}>{t("roster.lowPackage")}</Text>
                  </View>
                )}
                {item.paymentStatus && (
                  <Text style={{ fontSize: 11.5, color: theme.textSecondary }}>{t(statusKey(item.paymentStatus))}</Text>
                )}
              </View>
            </Card>
          </Pressable>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  list: { padding: Spacing.three },
  row: { flexDirection: "row", alignItems: "center", gap: Spacing.two },
  badge: { borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2 },
});
