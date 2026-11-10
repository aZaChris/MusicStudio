import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Beats } from "@/components/Beats";
import { Card } from "@/components/Card";
import { FilterChips } from "@/components/FilterChips";
import { Icon } from "@/components/Icon";
import { LogoutButton } from "@/components/LogoutButton";
import { QueryState } from "@/components/QueryState";
import { Screen, ScreenHeader, SectionTitle } from "@/components/Screen";
import { lessonTone, paymentTone, StatusChip } from "@/components/StatusChip";
import { Fonts, Radii, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { formatDateOfDateTime, formatDateTime, formatDay } from "@/lib/dates";
import { enumLabel, lessonStatusKey, paymentStatusKey, useLocale, useT } from "@/lib/i18n";
import { usePayments, useStudentLessons, useStudents } from "@/lib/queries";

/** Read-only by design: no action here changes data (spec US5). */
export default function ParentPortalScreen() {
  const c = useTheme();
  const t = useT();
  const locale = useLocale();
  const students = useStudents();
  const [activeId, setActiveId] = useState<number | null>(null);

  const children = students.data ?? [];
  const currentId = activeId ?? children[0]?.id ?? 0;
  const current = children.find((s) => s.id === currentId);
  const pkg = current?.active_package;
  const lessons = useStudentLessons(currentId);
  const payments = usePayments(currentId); // filtered by the server: ?student=<id>

  // The earliest lesson still to come.
  const now = new Date();
  const next = (lessons.data ?? [])
    .filter((l) => l.status === "scheduled" && new Date(l.start_time) >= now)
    .sort((a, b) => +new Date(a.start_time) - +new Date(b.start_time))[0];
  const money = new Intl.NumberFormat(locale === "it" ? "it-IT" : "en-GB", { style: "currency", currency: "EUR" });

  return (
    <Screen>
      <ScreenHeader title={t("parent.portalTitle")} right={<LogoutButton />} />
      <QueryState query={students} isEmpty={children.length === 0} emptyText={t("parent.noStudents")}>
        {children.length > 1 && (
          <FilterChips
            role="tab"
            accent
            options={children.map((s) => ({ id: s.id, label: s.full_name }))}
            value={currentId}
            onChange={setActiveId}
          />
        )}

        <View style={[styles.next, { backgroundColor: c.plum }]}>
          <View style={styles.nextTop}>
            <View style={styles.nextText}>
              <Text style={[Type.label, { color: c.plumSoft }]}>{t("parent.nextLesson")}</Text>
              <Text style={[styles.nextWhen, { color: c.onPlum }]}>{next ? formatDateTime(next.start_time, locale) : t("parent.noNextLesson")}</Text>
              <Text style={[Type.small, { color: c.plumSoft, fontSize: 15 }]}>{current?.instrument}</Text>
            </View>
            <Icon name="note" size={36} color={c.orange} strokeWidth={2} />
          </View>
          {pkg && (
            <View style={styles.nextBottom}>
              <Beats onPlum total={pkg.total_lessons} used={pkg.total_lessons - pkg.lessons_remaining} />
              <Text style={[Type.small, { color: c.onPlum, fontFamily: Fonts.bodyBold }]}>{t("parent.remaining", { count: String(pkg.lessons_remaining) })}</Text>
            </View>
          )}
        </View>

        <SectionTitle>{t("parent.lessons")}</SectionTitle>
        <QueryState query={lessons} isEmpty={(lessons.data ?? []).length === 0} emptyText={t("student.noLessons")}>
          <Card row style={styles.group}>
            {lessons.data?.map((lesson, i) => (
              <View key={lesson.id} style={[styles.line, i > 0 && { borderTopWidth: 1, borderTopColor: c.line2 }]}>
                <View style={styles.lineText}>
                  <Text style={[Type.body, { color: c.ink, fontFamily: Fonts.bodySemi }]}>{formatDateOfDateTime(lesson.start_time, locale)}</Text>
                  {!!lesson.notes && <Text style={[Type.small, { color: c.ink2 }]}>{lesson.notes}</Text>}
                </View>
                <StatusChip tone={lessonTone(lesson.status)} small label={enumLabel(t, lessonStatusKey(lesson.status))} />
              </View>
            ))}
          </Card>
        </QueryState>

        <SectionTitle>{t("parent.paymentStatus")}</SectionTitle>
        <QueryState query={payments} isEmpty={(payments.data ?? []).length === 0} emptyText={t("payments.empty")}>
          {payments.data?.map((item) => (
            <Card key={item.id} row style={styles.pay}>
              <Text style={[Type.bodyStrong, styles.lineText, { color: c.ink }]}>{formatDay(item.date, locale)}</Text>
              <View style={styles.payEnd}>
                <Text style={[Type.amount, { color: c.ink }]}>{money.format(Number(item.amount))}</Text>
                {item.status && <StatusChip tone={paymentTone(item.status)} small label={enumLabel(t, paymentStatusKey(item.status))} />}
              </View>
            </Card>
          ))}
        </QueryState>
      </QueryState>
    </Screen>
  );
}

const styles = StyleSheet.create({
  next: { borderRadius: Radii.card, padding: 18, gap: 14 },
  nextTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", gap: 12 },
  nextText: { flex: 1, gap: 2 },
  nextWhen: { fontFamily: Fonts.display, fontSize: 26, lineHeight: 30 },
  nextBottom: { gap: 8 },
  group: { paddingVertical: 4 },
  line: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, paddingVertical: 12 },
  lineText: { flex: 1, gap: 2 },
  pay: { flexDirection: "row", alignItems: "center", gap: 12 },
  payEnd: { alignItems: "flex-end", gap: 6 },
});
