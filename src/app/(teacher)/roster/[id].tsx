import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { Beats } from "@/components/Beats";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { IconButton } from "@/components/IconButton";
import { LessonSheet } from "@/components/forms/LessonSheet";
import { PackageSheet } from "@/components/forms/PackageSheet";
import { StudentSheet } from "@/components/forms/StudentSheet";
import { QueryState } from "@/components/QueryState";
import { Screen, SectionTitle } from "@/components/Screen";
import { lessonTone, packageTone, StatusChip } from "@/components/StatusChip";
import { Fonts, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { formatDateOfDateTime } from "@/lib/dates";
import { enumLabel, lessonStatusKey, useLocale, useT } from "@/lib/i18n";
import { useCancelLesson, useStudent, useStudentLessons } from "@/lib/queries";

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
  const cancelLesson = useCancelLesson();
  const [sheet, setSheet] = useState<"edit" | "package" | "lesson" | null>(null);

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

        <View style={styles.actions}>
          <Button title={t("lesson.schedule")} block onPress={() => setSheet("lesson")} />
          <View style={styles.actionsRow}>
            <View style={styles.half}>
              <Button title={t("package.new")} variant="secondary" block onPress={() => setSheet("package")} />
            </View>
            <View style={styles.half}>
              <Button title={t("student.edit")} variant="secondary" block onPress={() => setSheet("edit")} />
            </View>
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
              {lesson.status === "scheduled" && (
                <View style={styles.lessonActions}>
                  <Button
                    title={t("lesson.cancelLesson")}
                    variant="ghost"
                    disabled={cancelLesson.isPending}
                    onPress={() => cancelLesson.mutate({ id: lesson.id, status: "cancelled" })}
                  />
                  <Button
                    title={t("lesson.noShow")}
                    variant="ghost"
                    disabled={cancelLesson.isPending}
                    onPress={() => cancelLesson.mutate({ id: lesson.id, status: "no_show" })}
                  />
                </View>
              )}
            </Card>
          ))}
        </QueryState>
      </QueryState>

      {sheet === "edit" && student.data && <StudentSheet student={student.data} onClose={() => setSheet(null)} />}
      {sheet === "package" && student.data && (
        <PackageSheet studentId={student.data.id} studentName={student.data.full_name} onClose={() => setSheet(null)} />
      )}
      {sheet === "lesson" && student.data && (
        <LessonSheet studentId={student.data.id} studentName={student.data.full_name} onClose={() => setSheet(null)} />
      )}
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
  actions: { gap: 10 },
  actionsRow: { flexDirection: "row", gap: 10 },
  half: { flex: 1 },
  lesson: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 12 },
  lessonActions: { flexDirection: "row", width: "100%", justifyContent: "flex-end", gap: 4 },
  lessonText: { flex: 1, gap: 2 },
});
