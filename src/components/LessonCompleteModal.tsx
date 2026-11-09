import { useState } from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";

import { Fonts, Radius, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useT } from "@/lib/i18n";
import { ErrorText } from "./QueryState";
import { useCompleteLesson } from "@/lib/queries";
import { Button } from "./Button";
import { TextField } from "./TextField";

export function LessonCompleteModal({
  lessonId,
  studentName,
  onClose,
}: {
  lessonId: number;
  studentName: string;
  onClose: () => void;
}) {
  const theme = useTheme();
  const t = useT();
  const [note, setNote] = useState("");
  const completeLesson = useCompleteLesson();

  // On failure the dialog stays open with the server's reason (e.g. 409 already completed).
  const handleComplete = () => completeLesson.mutate({ id: lessonId, note }, { onSuccess: onClose });

  return (
    <Modal transparent animationType="fade" visible onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessible={false}>
        <Pressable
          accessibilityViewIsModal
          style={[styles.sheet, { backgroundColor: theme.backgroundElement }]}
        >
          <Text accessibilityRole="header" style={[styles.title, { color: theme.text }]}>
            {studentName}
          </Text>
          <TextField label={t("lesson.note")} value={note} onChangeText={setNote} multiline numberOfLines={3} />
          <ErrorText error={completeLesson.error} />
          <View style={styles.actions}>
            <Button title={t("lesson.cancel")} variant="secondary" onPress={onClose} />
            <Button title={t("lesson.markComplete")} onPress={handleComplete} loading={completeLesson.isPending} />
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.35)", alignItems: "center", justifyContent: "center" },
  sheet: { width: "88%", maxWidth: 360, borderRadius: Radius.lg, padding: Spacing.four, gap: Spacing.three },
  title: { fontFamily: Fonts.heading, fontSize: 17 },
  actions: { flexDirection: "row", gap: Spacing.two, justifyContent: "flex-end" },
});
