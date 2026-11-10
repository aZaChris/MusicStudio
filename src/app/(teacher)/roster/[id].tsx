import { useLocalSearchParams, useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { Beats } from "@/components/Beats";
import { Card } from "@/components/Card";
import { IconButton } from "@/components/IconButton";
import { QueryState } from "@/components/QueryState";
import { Screen, SectionTitle } from "@/components/Screen";
import { lessonTone, packageTone, StatusChip } from "@/components/StatusChip";
import { Fonts, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { formatDateOfDateTime } from "@/lib/dates";
import { enumLabel, lessonStatusKey, useLocale, useT } from "@/lib/i18n";
import { useStudent, useStudentLessons } from "@/lib/queries";

export default function StudentDetailScreen() {
  const c = useTheme();
  const t = useT();
  const locale = useLocale();
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const studentId = Number(id);
  const student = useStudent(studentId);
  const lessons = useStudentLessons(studentId);
  const pkg = student.data?.active_package;

  return (
    <Screen>
      <View style={styles.back}>
        <IconButton icon="back" label={t("nav.students")} onPress={() => router.back()} />
      </View>

      {/* A student that is not visible (404) shows a clear message, not an empty screen. */}
      <QueryState query={student}>
        <View style={styles.who}>
          <Avatar name={student.data?.full_name ?? ""} size={64} />
          <View style={styles.whoText}>
            <Text accessibilityRole="header" style={[Type.title, { color: c.ink, fontSize: 30, lineHeight: 33 }]}>
              {student.data?.full_name}
            </Text>
            <Text style={[Type.small, { color: c.ink2, fontSize: 15 }]}>{student.data?.instrument}</Text>
          </View>
        </View>

        <Card style={styles.package}>
          <View style={styles.packageHead}>
            <Text style={[Type.bodyStrong, { color: c.ink }]}>{t("roster.package")}</Text>
            {pkg && <StatusChip tone={packageTone(pkg.status)} small label={enumLabel(t, `package.status.${pkg.status}`)} />}
          </View>
          {pkg ? (
            <>
              <Beats size="l" total={pkg.total_lessons} used={pkg.total_lessons - pkg.lessons_remaining} />
              <Text style={[styles.remaining, { color: c.orangeText }]}>{t("roster.remainingCount", { count: String(pkg.lessons_remaining) })}</Text>
            </>
          ) : (
            <Text style={[Type.small, { color: c.ink2 }]}>{t("roster.noPackage")}</Text>
          )}
        </Card>

        <SectionTitle>{t("student.lessons")}</SectionTitle>
        <QueryState query={lessons} isEmpty={(lessons.data ?? []).length === 0} emptyText={t("student.noLessons")}>
          {lessons.data?.map((lesson) => (
            <Card key={lesson.id} row style={styles.lesson}>
              <View style={styles.lessonText}>
                <Text style={[Type.bodyStrong, { color: c.ink, fontSize: 15 }]}>{formatDateOfDateTime(lesson.start_time, locale)}</Text>
                {!!lesson.notes && <Text style={[Type.small, { color: c.ink2 }]}>{lesson.notes}</Text>}
              </View>
              <StatusChip tone={lessonTone(lesson.status)} small label={enumLabel(t, lessonStatusKey(lesson.status))} />
            </Card>
          ))}
        </QueryState>
      </QueryState>
    </Screen>
  );
}

const styles = StyleSheet.create({
  back: { alignItems: "flex-start" },
  who: { flexDirection: "row", alignItems: "center", gap: 14 },
  whoText: { flex: 1, gap: 2 },
  package: { gap: 12 },
  packageHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  remaining: { fontFamily: Fonts.display, fontSize: 18 },
  lesson: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 },
  lessonText: { flex: 1, gap: 2 },
});
