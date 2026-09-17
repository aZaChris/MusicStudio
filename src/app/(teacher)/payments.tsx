import { useState } from "react";
import { FlatList, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextField } from "@/components/TextField";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useT, type TranslationKey } from "@/lib/i18n";
import { useRegisterPayment, usePayments, useStudents, type Payment } from "@/lib/queries";

function statusKey(status: string): TranslationKey {
  return `payments.status${status.charAt(0).toUpperCase()}${status.slice(1)}` as TranslationKey;
}

const METHODS: Payment["method"][] = ["cash", "bank_transfer", "manual_entry"];

export default function PaymentsScreen() {
  const theme = useTheme();
  const t = useT();
  const { data } = usePayments();
  const { data: students } = useStudents();
  const registerPayment = useRegisterPayment();

  const [studentId, setStudentId] = useState<number | null>(null);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<Payment["method"]>("cash");

  const handleSubmit = async () => {
    if (!studentId || !amount) return;
    await registerPayment.mutateAsync({
      student: studentId,
      amount,
      date: new Date().toISOString().slice(0, 10),
      method,
      status: "paid",
    });
    setAmount("");
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.content}>
        <Card style={{ gap: Spacing.two }}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t("payments.registerPayment")}</Text>

          <Text style={{ fontFamily: Fonts.bodyBold, fontSize: 13, color: theme.textSecondary }}>
            {t("dashboard.activeStudents")}
          </Text>
          <View style={styles.chipRow}>
            {students?.results.map((s) => (
              <Pressable key={s.id} onPress={() => setStudentId(s.id)}>
                <View
                  style={[
                    styles.chip,
                    {
                      backgroundColor: studentId === s.id ? theme.accent : theme.backgroundMuted,
                      borderColor: theme.border,
                    },
                  ]}
                >
                  <Text style={{ color: studentId === s.id ? "white" : theme.text, fontSize: 12.5 }}>
                    {s.fullName}
                  </Text>
                </View>
              </Pressable>
            ))}
          </View>

          <TextField label={t("payments.amount")} value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />

          <View style={styles.chipRow}>
            {METHODS.map((m) => (
              <Pressable key={m} onPress={() => setMethod(m)}>
                <View
                  style={[
                    styles.chip,
                    { backgroundColor: method === m ? theme.accent : theme.backgroundMuted, borderColor: theme.border },
                  ]}
                >
                  <Text style={{ color: method === m ? "white" : theme.text, fontSize: 12.5 }}>{m}</Text>
                </View>
              </Pressable>
            ))}
          </View>

          <Button
            title={t("payments.registerPayment")}
            onPress={handleSubmit}
            loading={registerPayment.isPending}
            disabled={!studentId || !amount}
          />
        </Card>

        <FlatList
          data={data?.results ?? []}
          scrollEnabled={false}
          keyExtractor={(item) => String(item.id)}
          ItemSeparatorComponent={() => <View style={{ height: Spacing.two }} />}
          renderItem={({ item }) => (
            <Card style={styles.paymentRow}>
              <Text style={{ color: theme.text, fontSize: 13, flex: 1 }}>
                {item.studentFirstName} {item.studentLastName}
              </Text>
              <Text style={{ color: theme.text, fontSize: 13 }}>{item.amount}</Text>
              <Text style={{ color: theme.textSecondary, fontSize: 12 }}>{t(statusKey(item.status))}</Text>
            </Card>
          )}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.three, gap: Spacing.three },
  sectionTitle: { fontFamily: Fonts.bodyExtraBold, fontSize: 14 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one },
  chip: { borderRadius: 999, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 6 },
  paymentRow: { flexDirection: "row", alignItems: "center", gap: Spacing.two },
});
