import { useState } from "react";
import { FlatList, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "@/components/Card";
import { LessonCompleteModal } from "@/components/LessonCompleteModal";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";
import { useDashboard, type Lesson } from "@/lib/queries";

export default function HomeScreen() {
  const theme = useTheme();
  const t = useT();
  const { user } = useAuth();
  const { data, isLoading, refetch, isRefetching } = useDashboard();
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
      >
        <Text style={[styles.greeting, { color: theme.text }]}>
          {t("dashboard.greeting", { name: user?.email.split("@")[0] ?? "" })}
        </Text>

        {!isLoading && data && (
          <>
            <View style={styles.statsRow}>
              <Card style={styles.statCard}>
                <Text style={[styles.statValue, { color: theme.text }]}>{data.activeStudentsCount}</Text>
                <Text style={[styles.statLabel, { color: theme.textSecondary }]}>
                  {t("dashboard.activeStudents")}
                </Text>
              </Card>
              <Card style={styles.statCard}>
                <Text style={[styles.statValue, { color: theme.dangerText }]}>{data.pendingPaymentsCount}</Text>
                <Text style={[styles.statLabel, { color: theme.textSecondary }]}>
                  {t("dashboard.pendingPayments")}
                </Text>
              </Card>
            </View>

            <Text style={[styles.sectionTitle, { color: theme.text }]}>{t("dashboard.upcoming")}</Text>
            <FlatList
              data={data.upcoming}
              scrollEnabled={false}
              keyExtractor={(item) => String(item.id)}
              ItemSeparatorComponent={() => <View style={{ height: Spacing.two }} />}
              renderItem={({ item }) => (
                <Pressable onPress={() => item.status === "scheduled" && setActiveLesson(item)}>
                  <Card style={styles.lessonRow}>
                    <View
                      style={[
                        styles.avatar,
                        { backgroundColor: theme.backgroundMuted },
                      ]}
                    >
                      <Text style={{ fontFamily: Fonts.bodyExtraBold, fontSize: 12, color: theme.textSecondary }}>
                        {item.studentName[0]}
                        {item.studentLastName[0]}
                      </Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontFamily: Fonts.bodyBold, fontSize: 14, color: theme.text }}>
                        {item.studentName} {item.studentLastName}
                      </Text>
                      <Text style={{ fontSize: 12, color: theme.textSecondary }}>
                        {new Date(item.startTime).toLocaleString(undefined, {
                          weekday: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </Text>
                    </View>
                  </Card>
                </Pressable>
              )}
            />

            {data.lowPackageStudents.length > 0 && (
              <Card style={{ backgroundColor: theme.warningBg, borderColor: theme.warningBg }}>
                <Text style={{ color: theme.warningText, fontSize: 13 }}>
                  {data.lowPackageStudents.map((s) => s.fullName).join(", ")} — {t("roster.lowPackage")}
                </Text>
              </Card>
            )}
          </>
        )}
      </ScrollView>

      {activeLesson && (
        <LessonCompleteModal
          lessonId={activeLesson.id}
          studentName={`${activeLesson.studentName} ${activeLesson.studentLastName}`}
          onClose={() => setActiveLesson(null)}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.three, gap: Spacing.three },
  greeting: { fontFamily: Fonts.headingBold, fontSize: 22 },
  statsRow: { flexDirection: "row", gap: Spacing.two },
  statCard: { flex: 1 },
  statValue: { fontFamily: Fonts.headingBold, fontSize: 20 },
  statLabel: { fontSize: 11.5, marginTop: 2 },
  sectionTitle: { fontFamily: Fonts.bodyExtraBold, fontSize: 13 },
  lessonRow: { flexDirection: "row", alignItems: "center", gap: Spacing.two },
  avatar: { width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center" },
});
