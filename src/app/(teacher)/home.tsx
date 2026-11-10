import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Alert } from "@/components/Alert";
import { Card } from "@/components/Card";
import { IconButton } from "@/components/IconButton";
import { LessonCompleteModal } from "@/components/LessonCompleteModal";
import { LogoutButton } from "@/components/LogoutButton";
import { QueryState } from "@/components/QueryState";
import { Screen, ScreenHeader, SectionTitle } from "@/components/Screen";
import { StatCard } from "@/components/StatCard";
import { Fonts, Radii, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import type { Lesson } from "@/lib/api/types";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime } from "@/lib/dates";
import { useLocale, useT } from "@/lib/i18n";
import { useDashboard } from "@/lib/queries";

export default function HomeScreen() {
  const c = useTheme();
  const t = useT();
  const locale = useLocale();
  const router = useRouter();
  const { user } = useAuth();
  const dashboard = useDashboard();
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const data = dashboard.data;

  const tag = locale === "it" ? "it-IT" : "en-GB";
  const today = new Date();
  const eyebrow = new Intl.DateTimeFormat(tag, { weekday: "long", day: "numeric", month: "long" }).format(today);
  const timeOf = (iso: string) => new Intl.DateTimeFormat(tag, { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
  const dayOf = (iso: string) => {
    const d = new Date(iso);
    return d.toDateString() === today.toDateString() ? t("dashboard.today") : new Intl.DateTimeFormat(tag, { weekday: "short" }).format(d);
  };

  return (
    <Screen refreshControl={{ refreshing: dashboard.isRefetching, onRefresh: dashboard.refetch }}>
      <ScreenHeader
        eyebrow={eyebrow}
        // The backend user has no display name: the part of the email before "@".
        title={t("dashboard.greeting", { name: user?.email.split("@")[0] ?? "" })}
        right={<LogoutButton />}
      />

      <QueryState query={dashboard}>
        {data && (
          <>
            <View style={styles.stats}>
              <StatCard tone="plum" value={data.active_students_count} label={t("dashboard.activeStudents")} onPress={() => router.push("/(teacher)/roster")} />
              <StatCard tone="orange" value={data.pending_payments_count} label={t("dashboard.pendingPayments")} onPress={() => router.push("/(teacher)/payments")} />
            </View>

            {data.low_package_students.length > 0 && (
              <Alert kind="package" live={false}>
                {data.low_package_students.map((s) => s.full_name).join(", ")} — {t("roster.lowPackage")}
              </Alert>
            )}

            <SectionTitle>{t("dashboard.upcoming")}</SectionTitle>
            {data.upcoming.length === 0 && <Text style={[Type.small, { color: c.ink2 }]}>{t("dashboard.noUpcoming")}</Text>}
            {data.upcoming.map((lesson) => {
              const when = formatDateTime(lesson.start_time, locale);
              const canComplete = lesson.status === "scheduled";
              return (
                <Card key={lesson.id} row style={styles.lesson}>
                  <View style={[styles.timebox, { backgroundColor: c.paper }]}>
                    <Text style={[Type.amount, { color: c.ink }]}>{timeOf(lesson.start_time)}</Text>
                    <Text style={[styles.day, { color: c.ink2 }]}>{dayOf(lesson.start_time)}</Text>
                  </View>
                  <View style={styles.lessonText}>
                    <Text style={[Type.bodyStrong, { color: c.ink }]}>{lesson.student_name}</Text>
                    <Text style={[Type.small, { color: c.ink2 }]}>{t("dashboard.minutes", { count: String(lesson.duration_minutes) })}</Text>
                  </View>
                  {canComplete && (
                    <IconButton
                      icon="check"
                      tone="success"
                      label={`${t("lesson.markComplete")}: ${lesson.student_name}, ${when}`}
                      onPress={() => setActiveLesson(lesson)}
                    />
                  )}
                </Card>
              );
            })}
          </>
        )}
      </QueryState>

      {activeLesson && (
        <LessonCompleteModal
          lessonId={activeLesson.id}
          studentName={activeLesson.student_name}
          when={formatDateTime(activeLesson.start_time, locale)}
          onClose={() => setActiveLesson(null)}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  stats: { flexDirection: "row", gap: 12 },
  lesson: { flexDirection: "row", alignItems: "center", gap: 14 },
  timebox: { width: 60, alignItems: "center", paddingVertical: 8, borderRadius: Radii.field },
  day: { fontFamily: Fonts.bodySemi, fontSize: 12 },
  lessonText: { flex: 1, gap: 2 },
});
