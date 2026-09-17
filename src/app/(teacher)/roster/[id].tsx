import { useLocalSearchParams, useNavigation } from "expo-router";
import { useEffect } from "react";
import { FlatList, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "@/components/Card";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useT, type TranslationKey } from "@/lib/i18n";
import { useStudent, useStudentLessons } from "@/lib/queries";

function statusKey(status: string): TranslationKey {
  const camel = status
    .split("_")
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join("");
  return `lesson.status${camel}` as TranslationKey;
}

export default function StudentDetailScreen() {
  const theme = useTheme();
  const t = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const studentId = Number(id);
  const navigation = useNavigation();
  const { data: student } = useStudent(studentId);
  const { data: lessons } = useStudentLessons(studentId);

  useEffect(() => {
    if (student) navigation.setOptions({ title: student.fullName });
  }, [navigation, student]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.content}>
        {student && (
          <>
            <Text style={{ color: theme.textSecondary }}>{student.instrument}</Text>

            {student.activePackage && (
              <Card>
                <Text style={{ fontFamily: Fonts.bodyBold, color: theme.text }}>
                  {student.activePackage.lessonsRemaining}/{student.activePackage.totalLessons}{" "}
                  {t("roster.remaining")}
                </Text>
                <Text style={{ fontSize: 12, color: theme.textSecondary }}>{student.activePackage.status}</Text>
              </Card>
            )}

            <Text style={[styles.sectionTitle, { color: theme.text }]}>{t("dashboard.upcoming")}</Text>
            <FlatList
              data={lessons ?? []}
              scrollEnabled={false}
              keyExtractor={(item) => String(item.id)}
              ItemSeparatorComponent={() => <View style={{ height: Spacing.two }} />}
              renderItem={({ item }) => (
                <Card style={styles.lessonRow}>
                  <Text style={{ color: theme.text, fontSize: 13 }}>
                    {new Date(item.startTime).toLocaleDateString()}
                  </Text>
                  <Text style={{ color: theme.textSecondary, fontSize: 12 }}>{t(statusKey(item.status))}</Text>
                  {!!item.notes && (
                    <Text style={{ color: theme.textSecondary, fontSize: 12, flexShrink: 1 }}>{item.notes}</Text>
                  )}
                </Card>
              )}
            />
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.three, gap: Spacing.three },
  sectionTitle: { fontFamily: Fonts.bodyExtraBold, fontSize: 13 },
  lessonRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: Spacing.two },
});
