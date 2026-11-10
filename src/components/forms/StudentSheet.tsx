import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { BottomSheet } from "@/components/BottomSheet";
import { Button } from "@/components/Button";
import { FilterChips } from "@/components/FilterChips";
import { ErrorText } from "@/components/QueryState";
import { TextField } from "@/components/TextField";
import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import type { Student } from "@/lib/api/types";
import { savedTap } from "@/lib/haptics";
import { useT } from "@/lib/i18n";
import { useCreateStudent, useUpdateStudent } from "@/lib/queries";

/**
 * Add a student, or edit one (`student` given). Editing also lets the teacher archive the
 * student: the lists show active students only, nothing is deleted.
 */
export function StudentSheet({
  student,
  onClose,
  onSaved,
}: {
  student?: Student;
  onClose: () => void;
  onSaved?: (student: Student) => void;
}) {
  const c = useTheme();
  const t = useT();
  const [firstName, setFirstName] = useState(student?.first_name ?? "");
  const [lastName, setLastName] = useState(student?.last_name ?? "");
  const [instrument, setInstrument] = useState(student?.instrument ?? "");
  const [active, setActive] = useState(student?.is_active ?? true);
  const create = useCreateStudent();
  const update = useUpdateStudent(student?.id ?? 0);
  const mutation = student ? update : create;
  const ready = firstName.trim() && lastName.trim() && instrument.trim();

  const handleSave = () =>
    mutation.mutate(
      {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        instrument: instrument.trim(),
        ...(student ? { is_active: active } : {}),
      },
      {
        onSuccess: (saved) => {
          savedTap();
          onSaved?.(saved);
          onClose();
        },
      },
    );

  const title = student ? t("student.edit") : t("student.new");
  return (
    <BottomSheet title={title} onClose={onClose}>
      <Text accessibilityRole="header" style={[Type.heading, { color: c.ink, fontSize: 24 }]}>
        {title}
      </Text>
      <TextField label={t("student.firstName")} value={firstName} onChangeText={setFirstName} autoCapitalize="words" maxLength={100} />
      <TextField label={t("student.lastName")} value={lastName} onChangeText={setLastName} autoCapitalize="words" maxLength={100} />
      <TextField label={t("student.instrument")} value={instrument} onChangeText={setInstrument} autoCapitalize="sentences" maxLength={100} />
      {student && (
        <View style={styles.block}>
          <FilterChips
            role="radio"
            options={[
              { id: "yes", label: t("student.active") },
              { id: "no", label: t("student.archived") },
            ]}
            value={active ? "yes" : "no"}
            onChange={(id) => setActive(id === "yes")}
          />
          <Text style={[Type.small, { color: c.ink2 }]}>{t("student.archiveHint")}</Text>
        </View>
      )}
      <ErrorText error={mutation.error} />
      <Button title={t("common.save")} large block onPress={handleSave} loading={mutation.isPending} disabled={!ready} />
    </BottomSheet>
  );
}

const styles = StyleSheet.create({ block: { gap: 8 } });
