import { useState } from "react";
import { Text } from "react-native";

import { BottomSheet } from "@/components/BottomSheet";
import { Button } from "@/components/Button";
import { FilterChips } from "@/components/FilterChips";
import { ErrorText } from "@/components/QueryState";
import { TextField } from "@/components/TextField";
import { Fonts, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { localDateTimeToISO, nextDays } from "@/lib/dates";
import { savedTap } from "@/lib/haptics";
import { useLocale, useT } from "@/lib/i18n";
import { useCreateLesson } from "@/lib/queries";

// Every half hour from 08:00 to 21:30: picking beats typing on a phone.
const TIMES = Array.from({ length: 28 }, (_, i) => {
  const minutes = 8 * 60 + i * 30;
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
});
const DURATIONS = [30, 45, 60, 90] as const;

/**
 * Schedule a lesson. The server attaches the student's active package; an overlap with another
 * lesson of the same teacher comes back as a 409 with the reason, shown in the sheet.
 */
export function LessonSheet({
  studentId,
  studentName,
  onClose,
}: {
  studentId: number;
  studentName: string;
  onClose: () => void;
}) {
  const c = useTheme();
  const t = useT();
  const locale = useLocale();
  const days = nextDays(21);
  const [day, setDay] = useState(days[0]);
  const [time, setTime] = useState("16:00");
  const [minutes, setMinutes] = useState("45");
  const [notes, setNotes] = useState("");
  const create = useCreateLesson();

  const tag = locale === "it" ? "it-IT" : "en-GB";
  const dayLabel = (iso: string, i: number) => {
    if (i === 0) return t("dashboard.today");
    if (i === 1) return t("dashboard.tomorrow");
    const [y, m, d] = iso.split("-").map(Number);
    return new Intl.DateTimeFormat(tag, { weekday: "short", day: "numeric", month: "short" }).format(new Date(y, m - 1, d));
  };

  const handleSave = () =>
    create.mutate(
      { student: studentId, start_time: localDateTimeToISO(day, time), duration_minutes: Number(minutes), notes },
      {
        onSuccess: () => {
          savedTap();
          onClose();
        },
      },
    );

  return (
    <BottomSheet title={t("lesson.schedule")} onClose={onClose}>
      <Text accessibilityRole="header" style={[Type.heading, { color: c.ink, fontSize: 24 }]}>
        {t("lesson.schedule")}
      </Text>
      <Text style={[Type.small, { color: c.ink2 }]}>{studentName}</Text>

      <Text style={[Type.small, { color: c.ink, fontFamily: Fonts.bodyBold }]}>{t("lesson.day")}</Text>
      <FilterChips scroll role="radio" options={days.map((d, i) => ({ id: d, label: dayLabel(d, i) }))} value={day} onChange={setDay} />

      <Text style={[Type.small, { color: c.ink, fontFamily: Fonts.bodyBold }]}>{t("lesson.time")}</Text>
      <FilterChips scroll role="radio" options={TIMES.map((x) => ({ id: x, label: x }))} value={time} onChange={setTime} />

      <Text style={[Type.small, { color: c.ink, fontFamily: Fonts.bodyBold }]}>{t("lesson.duration")}</Text>
      <FilterChips
        role="radio"
        options={DURATIONS.map((m) => ({ id: String(m), label: t("dashboard.minutes", { count: String(m) }) }))}
        value={minutes}
        onChange={setMinutes}
      />

      <TextField label={t("lesson.noteOptional")} value={notes} onChangeText={setNotes} multiline />
      <ErrorText error={create.error} />
      <Button title={t("common.save")} large block onPress={handleSave} loading={create.isPending} />
    </BottomSheet>
  );
}
