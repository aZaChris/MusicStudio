import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Alert } from "@/components/Alert";
import { BottomSheet } from "@/components/BottomSheet";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { FilterChips } from "@/components/FilterChips";
import { Icon } from "@/components/Icon";
import { PressScale } from "@/components/Motion";
import { ErrorText, QueryState } from "@/components/QueryState";
import { Screen, ScreenHeader } from "@/components/Screen";
import { paymentTone, StatusChip } from "@/components/StatusChip";
import { TextField } from "@/components/TextField";
import { Fonts, shadow, Type } from "@/constants/theme";
import { useScheme, useTheme } from "@/hooks/use-theme";
import type { PaymentMethod } from "@/lib/api/types";
import { formatDay, localDateISO } from "@/lib/dates";
import { savedTap } from "@/lib/haptics";
import { enumLabel, paymentMethodKey, paymentStatusKey, useLocale, useT } from "@/lib/i18n";
import { usePayments, useRegisterPayment, useStudents } from "@/lib/queries";

// Online card payments come from Stripe webhooks, never from this form.
const MANUAL_METHODS: PaymentMethod[] = ["cash", "bank_transfer", "manual_entry"];

type Filter = "all" | "pending" | "paid";

export default function PaymentsScreen() {
  const c = useTheme();
  const scheme = useScheme();
  const t = useT();
  const locale = useLocale();
  const payments = usePayments();
  const students = useStudents();
  const registerPayment = useRegisterPayment();

  const [filter, setFilter] = useState<Filter>("all");
  const [formOpen, setFormOpen] = useState(false);
  const [studentId, setStudentId] = useState<number | null>(null);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("cash");

  const handleSubmit = () => {
    if (!studentId || !amount) return;
    registerPayment.mutate(
      // Local calendar date: after midnight in Italy the UTC date is still yesterday.
      { student: studentId, amount: amount.replace(",", "."), date: localDateISO(), method, status: "paid" },
      {
        onSuccess: () => {
          setAmount("");
          savedTap();
        }, // on failure the form keeps what the user typed
      },
    );
  };

  const all = payments.data ?? [];
  const shown = all.filter((p) => filter === "all" || (filter === "paid" ? p.status === "paid" : p.status !== "paid"));
  const toCollect = all.filter((p) => p.status !== "paid").length;
  const money = new Intl.NumberFormat(locale === "it" ? "it-IT" : "en-GB", { style: "currency", currency: "EUR" });

  return (
    <SafeAreaView style={[styles.fill, { backgroundColor: c.paper }]} edges={["top"]}>
      <Screen edges={[]} padBottom={false}>
        <ScreenHeader title={t("payments.title")} eyebrow={t("payments.toCollect", { count: String(toCollect) })} />
        <FilterChips
          options={[
            { id: "all", label: t("payments.filter.all") },
            { id: "pending", label: t("payments.filter.pending") },
            { id: "paid", label: t("payments.filter.paid") },
          ]}
          value={filter}
          onChange={setFilter}
        />
        <QueryState query={payments} isEmpty={all.length === 0} emptyText={t("payments.empty")}>
          <View style={styles.list}>
            {shown.map((item) => (
              <Card key={item.id} row style={styles.row}>
                <View style={styles.rowText}>
                  <Text style={[Type.bodyStrong, { color: c.ink }]}>{item.student_name}</Text>
                  <Text style={[Type.small, { color: c.ink2 }]}>
                    {formatDay(item.date, locale)} · {enumLabel(t, paymentMethodKey(item.method))}
                  </Text>
                </View>
                <View style={styles.rowEnd}>
                  <Text style={[Type.amount, { color: c.ink }]}>{money.format(Number(item.amount))}</Text>
                  {item.status && <StatusChip tone={paymentTone(item.status)} small label={enumLabel(t, paymentStatusKey(item.status))} />}
                </View>
              </Card>
            ))}
          </View>
        </QueryState>
        <View style={styles.fabSpace} />
      </Screen>

      {!formOpen && (
        <PressScale
          accessibilityRole="button"
          accessibilityLabel={t("payments.registerPayment")}
          onPress={() => setFormOpen(true)}
          style={[styles.fab, { backgroundColor: c.orange }, shadow("float", scheme)]}
        >
          <Icon name="plus" size={20} color={c.onOrange} strokeWidth={2.4} />
          <Text style={[styles.fabText, { color: c.onOrange }]}>{t("payments.registerPayment")}</Text>
        </PressScale>
      )}

      {formOpen && (
        <BottomSheet title={t("payments.registerPayment")} onClose={() => setFormOpen(false)}>
          <Text accessibilityRole="header" style={[Type.heading, { color: c.ink, fontSize: 24 }]}>
            {t("payments.registerPayment")}
          </Text>

          <Text style={[styles.label, { color: c.ink }]}>{t("payments.student")}</Text>
          <QueryState query={students} isEmpty={(students.data ?? []).length === 0} emptyText={t("roster.empty")}>
            <FilterChips
              role="radio"
              options={(students.data ?? []).map((s) => ({ id: s.id, label: s.full_name }))}
              value={studentId}
              onChange={setStudentId}
            />
          </QueryState>

          <TextField label={t("payments.amount")} value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />

          <Text style={[styles.label, { color: c.ink }]}>{t("payments.method")}</Text>
          <FilterChips
            role="radio"
            options={MANUAL_METHODS.map((m) => ({ id: m, label: t(paymentMethodKey(m)) }))}
            value={method}
            onChange={setMethod}
          />

          <ErrorText error={registerPayment.error} />
          {registerPayment.isSuccess && !amount && <Alert kind="success">{t("payments.saved")}</Alert>}

          <Button
            title={t("payments.registerPayment")}
            large
            block
            onPress={handleSubmit}
            loading={registerPayment.isPending}
            disabled={!studentId || !amount}
          />
        </BottomSheet>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  list: { gap: 10 },
  row: { flexDirection: "row", alignItems: "center", gap: 12 },
  rowText: { flex: 1, gap: 3 },
  rowEnd: { alignItems: "flex-end", gap: 6 },
  label: { fontFamily: Fonts.bodyBold, fontSize: 13 },
  fabSpace: { height: 72 },
  fab: {
    position: "absolute",
    right: 20,
    bottom: 20,
    height: 56,
    paddingLeft: 18,
    paddingRight: 22,
    borderRadius: 999,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  fabText: { fontFamily: Fonts.bodyBold, fontSize: 16 },
});
