import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ErrorText, QueryState } from "@/components/QueryState";
import { TextField } from "@/components/TextField";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import type { PaymentMethod } from "@/lib/api/types";
import { formatDay, localDateISO } from "@/lib/dates";
import { enumLabel, paymentMethodKey, paymentStatusKey, useLocale, useT } from "@/lib/i18n";
import { usePayments, useRegisterPayment, useStudents } from "@/lib/queries";

// Online card payments come from Stripe webhooks, never from this form.
const MANUAL_METHODS: PaymentMethod[] = ["cash", "bank_transfer", "manual_entry"];

function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      accessibilityLabel={label}
    >
      <View
        style={[
          styles.chip,
          { backgroundColor: selected ? theme.accent : theme.backgroundMuted, borderColor: theme.border },
        ]}
      >
        <Text style={{ color: selected ? "white" : theme.text, fontSize: 12.5 }}>{label}</Text>
      </View>
    </Pressable>
  );
}

export default function PaymentsScreen() {
  const theme = useTheme();
  const t = useT();
  const locale = useLocale();
  const payments = usePayments();
  const students = useStudents();
  const registerPayment = useRegisterPayment();

  const [studentId, setStudentId] = useState<number | null>(null);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("cash");

  const handleSubmit = () => {
    if (!studentId || !amount) return;
    registerPayment.mutate(
      // Local calendar date: after midnight in Italy the UTC date is still yesterday.
      { student: studentId, amount: amount.replace(",", "."), date: localDateISO(), method, status: "paid" },
      { onSuccess: () => setAmount("") }, // on failure the form keeps what the user typed
    );
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.content}>
        <Card style={{ gap: Spacing.two }}>
          <Text accessibilityRole="header" style={[styles.sectionTitle, { color: theme.text }]}>
            {t("payments.registerPayment")}
          </Text>

          <Text style={[styles.label, { color: theme.textSecondary }]}>{t("payments.student")}</Text>
          <QueryState query={students} isEmpty={(students.data ?? []).length === 0} emptyText={t("roster.empty")}>
            <View style={styles.chipRow} accessibilityRole="radiogroup">
              {students.data?.map((s) => (
                <Chip key={s.id} label={s.full_name} selected={studentId === s.id} onPress={() => setStudentId(s.id)} />
              ))}
            </View>
          </QueryState>

          <TextField
            label={t("payments.amount")}
            value={amount}
            onChangeText={setAmount}
            keyboardType="decimal-pad"
          />

          <Text style={[styles.label, { color: theme.textSecondary }]}>{t("payments.method")}</Text>
          <View style={styles.chipRow} accessibilityRole="radiogroup">
            {MANUAL_METHODS.map((m) => (
              <Chip key={m} label={t(paymentMethodKey(m))} selected={method === m} onPress={() => setMethod(m)} />
            ))}
          </View>

          <ErrorText error={registerPayment.error} />
          {registerPayment.isSuccess && !amount && (
            <Text accessibilityLiveRegion="polite" style={{ color: theme.successText }}>
              {t("payments.saved")}
            </Text>
          )}

          <Button
            title={t("payments.registerPayment")}
            onPress={handleSubmit}
            loading={registerPayment.isPending}
            disabled={!studentId || !amount}
          />
        </Card>

        <QueryState query={payments} isEmpty={(payments.data ?? []).length === 0} emptyText={t("payments.empty")}>
          {payments.data?.map((item) => (
            <Card key={item.id} style={styles.paymentRow}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: theme.text, fontSize: 13 }}>{item.student_name}</Text>
                <Text style={{ color: theme.textSecondary, fontSize: 12 }}>
                  {formatDay(item.date, locale)} · {enumLabel(t, paymentMethodKey(item.method))}
                </Text>
              </View>
              <Text style={{ color: theme.text, fontSize: 13 }}>€ {item.amount}</Text>
              {item.status && (
                <Text style={{ color: theme.textSecondary, fontSize: 12 }}>
                  {enumLabel(t, paymentStatusKey(item.status))}
                </Text>
              )}
            </Card>
          ))}
        </QueryState>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.three, gap: Spacing.three },
  sectionTitle: { fontFamily: Fonts.bodyExtraBold, fontSize: 14 },
  label: { fontFamily: Fonts.bodyBold, fontSize: 13 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one },
  chip: { borderRadius: 999, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 6 },
  paymentRow: { flexDirection: "row", alignItems: "center", gap: Spacing.two },
});
