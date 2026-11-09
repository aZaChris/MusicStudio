import { useState } from "react";
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "@/components/Card";
import { LessonCompleteModal } from "@/components/LessonCompleteModal";
import { QueryState } from "@/components/QueryState";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import type { Lesson } from "@/lib/api/types";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime } from "@/lib/dates";
import { useLocale, useT } from "@/lib/i18n";
import { useDashboard } from "@/lib/queries";

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function HomeScreen() {
  const theme = useTheme();
  const t = useT();
  const locale = useLocale();
  const { user } = useAuth();
  const dashboard = useDashboard();
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const data = dashboard.data;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={dashboard.isRefetching} onRefresh={dashboard.refetch} />}
      >
        <Text accessibilityRole="header" style={[styles.greeting, { color: theme.text }]}>
          {/* The backend user has no display name: the part of the email before "@". */}
          {t("dashboard.greeting", { name: user?.email.split("@")[0] ?? "" })}
        </Text>

        <QueryState query={dashboard}>
          {data && (
            <>
              <View style={styles.statsRow}>
                <Card style={styles.statCard}>
                  <Text style={[styles.statValue, { color: theme.text }]}>{data.active_students_count}</Text>
                  <Text style={[styles.statLabel, { color: theme.textSecondary }]}>
                    {t("dashboard.activeStudents")}
                  </Text>
                </Card>
                <Card style={styles.statCard}>
                  <Text style={[styles.statValue, { color: theme.dangerText }]}>{data.pending_payments_count}</Text>
                  <Text style={[styles.statLabel, { color: theme.textSecondary }]}>
                    {t("dashboard.pendingPayments")}
                  </Text>
                </Card>
              </View>

              <Text accessibilityRole="header" style={[styles.sectionTitle, { color: theme.text }]}>
                {t("dashboard.upcoming")}
              </Text>
              {data.upcoming.length === 0 && (
                <Text style={{ color: theme.textSecondary }}>{t("dashboard.noUpcoming")}</Text>
              )}
              {data.upcoming.map((lesson) => {
                const when = formatDateTime(lesson.start_time, locale);
                const canComplete = lesson.status === "scheduled";
                return (
                  <Pressable
                    key={lesson.id}
                    accessibilityRole={canComplete ? "button" : undefined}
                    accessibilityLabel={`${lesson.student_name}, ${when}`}
                    accessibilityHint={canComplete ? t("lesson.markComplete") : undefined}
                    disabled={!canComplete}
                    onPress={() => setActiveLesson(lesson)}
                  >
                    <Card style={styles.lessonRow}>
                      <View style={[styles.avatar, { backgroundColor: theme.backgroundMuted }]}>
                        <Text style={{ fontFamily: Fonts.bodyExtraBold, fontSize: 12, color: theme.textSecondary }}>
                          {initials(lesson.student_name)}
                        </Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={{ fontFamily: Fonts.bodyBold, fontSize: 14, color: theme.text }}>
                          {lesson.student_name}
                        </Text>
                        <Text style={{ fontSize: 12, color: theme.textSecondary }}>{when}</Text>
                      </View>
                    </Card>
                  </Pressable>
                );
              })}

              {data.low_package_students.length > 0 && (
                <Card style={{ backgroundColor: theme.warningBg, borderColor: theme.warningBg }}>
                  <Text style={{ color: theme.warningText, fontSize: 13 }}>
                    {data.low_package_students.map((s) => s.full_name).join(", ")} — {t("roster.lowPackage")}
                  </Text>
                </Card>
              )}
            </>
          )}
        </QueryState>
      </ScrollView>

      {activeLesson && (
        <LessonCompleteModal
          lessonId={activeLesson.id}
          studentName={activeLesson.student_name}
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
