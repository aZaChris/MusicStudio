import { useLocalSearchParams, useNavigation } from "expo-router";
import { useEffect } from "react";
import { ScrollView, StyleSheet, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "@/components/Card";
import { QueryState } from "@/components/QueryState";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { formatDateOfDateTime } from "@/lib/dates";
import { enumLabel, lessonStatusKey, useLocale, useT } from "@/lib/i18n";
import { useStudent, useStudentLessons } from "@/lib/queries";

export default function StudentDetailScreen() {
  const theme = useTheme();
  const t = useT();
  const locale = useLocale();
  const { id } = useLocalSearchParams<{ id: string }>();
  const studentId = Number(id);
  const navigation = useNavigation();
  const student = useStudent(studentId);
  const lessons = useStudentLessons(studentId);
  const pkg = student.data?.active_package;

  useEffect(() => {
    if (student.data) navigation.setOptions({ title: student.data.full_name });
  }, [navigation, student.data]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* A student that is not visible (404) shows a clear message, not an empty screen. */}
        <QueryState query={student}>
          <Text style={{ color: theme.textSecondary }}>{student.data?.instrument}</Text>
          <Card>
            {pkg ? (
              <>
                <Text style={{ fontFamily: Fonts.bodyBold, color: theme.text }}>
                  {pkg.lessons_remaining}/{pkg.total_lessons} {t("roster.remaining")}
                </Text>
                <Text style={{ fontSize: 12, color: theme.textSecondary }}>
                  {enumLabel(t, `package.status.${pkg.status}`)}
                </Text>
              </>
            ) : (
              <Text style={{ color: theme.textSecondary }}>{t("roster.noPackage")}</Text>
            )}
          </Card>

          <Text accessibilityRole="header" style={[styles.sectionTitle, { color: theme.text }]}>
            {t("student.lessons")}
          </Text>
          <QueryState
            query={lessons}
            isEmpty={(lessons.data ?? []).length === 0}
            emptyText={t("student.noLessons")}
          >
            {lessons.data?.map((lesson) => (
              <Card key={lesson.id} style={styles.lessonRow}>
                <Text style={{ color: theme.text, fontSize: 13 }}>
                  {formatDateOfDateTime(lesson.start_time, locale)}
                </Text>
                <Text style={{ color: theme.textSecondary, fontSize: 12 }}>
                  {enumLabel(t, lessonStatusKey(lesson.status))}
                </Text>
                {!!lesson.notes && (
                  <Text style={{ color: theme.textSecondary, fontSize: 12, flexShrink: 1 }}>{lesson.notes}</Text>
                )}
              </Card>
            ))}
          </QueryState>
        </QueryState>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.three, gap: Spacing.three },
  sectionTitle: { fontFamily: Fonts.bodyExtraBold, fontSize: 13 },
  lessonRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: Spacing.two },
});
