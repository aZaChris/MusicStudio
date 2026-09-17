import { useNavigation } from "expo-router";
import { useEffect, useState } from "react";
import { FlatList, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "@/components/Card";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";
import { useT, type TranslationKey } from "@/lib/i18n";
import { usePayments, useStudentLessons, useStudents } from "@/lib/queries";

function lessonStatusKey(status: string): TranslationKey {
  const camel = status
    .split("_")
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join("");
  return `lesson.status${camel}` as TranslationKey;
}

function paymentStatusKey(status: string): TranslationKey {
  return `payments.status${status.charAt(0).toUpperCase()}${status.slice(1)}` as TranslationKey;
}

export default function ParentPortalScreen() {
  const theme = useTheme();
  const t = useT();
  const navigation = useNavigation();
  const { logout } = useAuth();
  const { data: students } = useStudents();
  const [activeId, setActiveId] = useState<number | null>(null);

  const currentId = activeId ?? students?.results[0]?.id ?? 0;
  const { data: lessons } = useStudentLessons(currentId);
  const { data: payments } = usePayments();
  const studentPayments = payments?.results.filter((p) => p.studentId === currentId) ?? [];

  useEffect(() => {
    navigation.setOptions({
      title: t("parent.portalTitle"),
      headerRight: () => (
        <Pressable onPress={logout} hitSlop={12}>
          <Text style={{ color: theme.accent, fontSize: 14 }}>{t("auth.logout")}</Text>
        </Pressable>
      ),
    });
  }, [navigation, t, logout, theme.accent]);

  if (students && students.results.length === 0) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }}>
        <Text style={{ padding: Spacing.four, color: theme.textSecondary }}>{t("parent.noStudents")}</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.content}>
        {students && students.results.length > 1 && (
          <View style={styles.chipRow}>
            {students.results.map((s) => (
              <Pressable key={s.id} onPress={() => setActiveId(s.id)}>
                <View
                  style={[
                    styles.chip,
                    { backgroundColor: currentId === s.id ? theme.accent : theme.backgroundElement, borderColor: theme.border },
                  ]}
                >
                  <Text style={{ color: currentId === s.id ? "white" : theme.text, fontSize: 12.5 }}>
                    {s.fullName}
                  </Text>
                </View>
              </Pressable>
            ))}
          </View>
        )}

        <Text style={[styles.sectionTitle, { color: theme.text }]}>
          {t("parent.upcomingLessons")} / {t("parent.attendance")}
        </Text>
        <FlatList
          data={lessons ?? []}
          scrollEnabled={false}
          keyExtractor={(item) => String(item.id)}
          ItemSeparatorComponent={() => <View style={{ height: Spacing.two }} />}
          renderItem={({ item }) => (
            <Card style={styles.row}>
              <Text style={{ color: theme.text, fontSize: 13 }}>
                {new Date(item.startTime).toLocaleDateString()}
              </Text>
              <Text style={{ color: theme.textSecondary, fontSize: 12 }}>{t(lessonStatusKey(item.status))}</Text>
              {!!item.notes && <Text style={{ color: theme.textSecondary, fontSize: 12 }}>{item.notes}</Text>}
            </Card>
          )}
        />

        <Text style={[styles.sectionTitle, { color: theme.text }]}>{t("parent.paymentStatus")}</Text>
        <FlatList
          data={studentPayments}
          scrollEnabled={false}
          keyExtractor={(item) => String(item.id)}
          ItemSeparatorComponent={() => <View style={{ height: Spacing.two }} />}
          renderItem={({ item }) => (
            <Card style={styles.row}>
              <Text style={{ color: theme.text, fontSize: 13 }}>{item.date}</Text>
              <Text style={{ color: theme.text, fontSize: 13 }}>{item.amount}</Text>
              <Text style={{ color: theme.textSecondary, fontSize: 12 }}>{t(paymentStatusKey(item.status))}</Text>
            </Card>
          )}
        />
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
