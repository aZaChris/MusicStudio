import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { savedTap } from "@/lib/haptics";
import { useT } from "@/lib/i18n";
import { useCompleteLesson } from "@/lib/queries";
import { BottomSheet } from "./BottomSheet";
import { Button } from "./Button";
import { ErrorText } from "./QueryState";
import { TextField } from "./TextField";

/** "Mark as completed": a note, then Complete. The panel stays open on failure, with the reason. */
export function LessonCompleteModal({
  lessonId,
  studentName,
  when,
  onClose,
}: {
  lessonId: number;
  studentName: string;
  when?: string;
  onClose: () => void;
}) {
  const c = useTheme();
  const t = useT();
  const [note, setNote] = useState("");
  const completeLesson = useCompleteLesson();

  const handleComplete = () =>
    completeLesson.mutate(
      { id: lessonId, note },
      {
        onSuccess: () => {
          savedTap();
          onClose();
        },
      },
    );

  return (
    <BottomSheet title={t("lesson.markComplete")} onClose={onClose}>
      <View style={styles.titles}>
        <Text accessibilityRole="header" style={[Type.heading, { color: c.ink, fontSize: 24 }]}>
          {t("lesson.markComplete")}
        </Text>
        <Text style={[Type.small, { color: c.ink2 }]}>{when ? `${studentName} · ${when}` : studentName}</Text>
      </View>
      <TextField label={t("lesson.note")} value={note} onChangeText={setNote} multiline />
      <ErrorText error={completeLesson.error} />
      <View style={styles.actions}>
        <View style={styles.half}>
          <Button title={t("lesson.cancel")} variant="secondary" block onPress={onClose} />
        </View>
        <View style={styles.half}>
          <Button title={t("lesson.complete")} block onPress={handleComplete} loading={completeLesson.isPending} />
        </View>
      </View>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  titles: { gap: 4 },
  actions: { flexDirection: "row", gap: 10 },
  half: { flex: 1 },
});
