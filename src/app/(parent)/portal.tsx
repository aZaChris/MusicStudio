import { useNavigation } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "@/components/Card";
import { LogoutButton } from "@/components/LogoutButton";
import { QueryState } from "@/components/QueryState";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { formatDateOfDateTime, formatDay } from "@/lib/dates";
import { enumLabel, lessonStatusKey, paymentStatusKey, useLocale, useT } from "@/lib/i18n";
import { usePayments, useStudentLessons, useStudents } from "@/lib/queries";

/** Read-only by design: no action here changes data (spec US5). */
export default function ParentPortalScreen() {
  const theme = useTheme();
  const t = useT();
  const locale = useLocale();
  const navigation = useNavigation();
  const students = useStudents();
  const [activeId, setActiveId] = useState<number | null>(null);

  const children = students.data ?? [];
  const currentId = activeId ?? children[0]?.id ?? 0;
  const lessons = useStudentLessons(currentId);
  const payments = usePayments(currentId); // filtered by the server: ?student=<id>

  useEffect(() => {
    navigation.setOptions({ title: t("parent.portalTitle"), headerRight: () => <LogoutButton /> });
  }, [navigation, t]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.content}>
        <QueryState query={students} isEmpty={children.length === 0} emptyText={t("parent.noStudents")}>
          {children.length > 1 && (
            <View style={styles.chipRow} accessibilityRole="tablist">
              {children.map((s) => {
                const selected = currentId === s.id;
                return (
                  <Pressable
                    key={s.id}
                    onPress={() => setActiveId(s.id)}
                    accessibilityRole="tab"
                    accessibilityState={{ selected }}
                    accessibilityLabel={s.full_name}
                  >
                    <View
                      style={[
                        styles.chip,
                        { backgroundColor: selected ? theme.accent : theme.backgroundElement, borderColor: theme.border },
                      ]}
                    >
                      <Text style={{ color: selected ? "white" : theme.text, fontSize: 12.5 }}>{s.full_name}</Text>
                    </View>
                  </Pressable>
                );
              })}
            </View>
          )}

          <Text accessibilityRole="header" style={[styles.sectionTitle, { color: theme.text }]}>
            {t("parent.lessons")}
          </Text>
          <QueryState
            query={lessons}
            isEmpty={(lessons.data ?? []).length === 0}
            emptyText={t("student.noLessons")}
          >
            {lessons.data?.map((lesson) => (
              <Card key={lesson.id} style={styles.row}>
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

          <Text accessibilityRole="header" style={[styles.sectionTitle, { color: theme.text }]}>
            {t("parent.paymentStatus")}
          </Text>
          <QueryState
            query={payments}
            isEmpty={(payments.data ?? []).length === 0}
            emptyText={t("payments.empty")}
          >
            {payments.data?.map((item) => (
              <Card key={item.id} style={styles.row}>
                <Text style={{ color: theme.text, fontSize: 13 }}>{formatDay(item.date, locale)}</Text>
                <Text style={{ color: theme.text, fontSize: 13 }}>€ {item.amount}</Text>
                {item.status && (
                  <Text style={{ color: theme.textSecondary, fontSize: 12 }}>
                    {enumLabel(t, paymentStatusKey(item.status))}
                  </Text>
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
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one },
  chip: { borderRadius: 999, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 6 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: Spacing.two },
});
