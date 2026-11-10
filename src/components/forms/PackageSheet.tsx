import { useState } from "react";
import { Text } from "react-native";

import { BottomSheet } from "@/components/BottomSheet";
import { Button } from "@/components/Button";
import { FilterChips } from "@/components/FilterChips";
import { ErrorText } from "@/components/QueryState";
import { TextField } from "@/components/TextField";
import { Fonts, Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { addMonths, formatDay, localDateISO } from "@/lib/dates";
import { savedTap } from "@/lib/haptics";
import { useLocale, useT } from "@/lib/i18n";
import { useCreatePackage } from "@/lib/queries";

const SIZES = [5, 10, 20] as const;
type Expiry = "none" | "3" | "6" | "12";

/** Sell a package of lessons. Bought today; the price is what was agreed, typed by the teacher. */
export function PackageSheet({
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
  const [lessons, setLessons] = useState("10");
  const [price, setPrice] = useState("");
  const [expiry, setExpiry] = useState<Expiry>("none");
  const create = useCreatePackage();
  // Local calendar date: after midnight in Italy the UTC date is still yesterday.
  const today = localDateISO();
  const total = Number(lessons);
  const ready = Number.isInteger(total) && total > 0 && price.trim() !== "";

  const handleSave = () =>
    create.mutate(
      {
        student: studentId,
        total_lessons: total,
        price: price.replace(",", "."),
        purchase_date: today,
        expiry_date: expiry === "none" ? null : addMonths(today, Number(expiry)),
      },
      {
        onSuccess: () => {
          savedTap();
          onClose();
        },
      },
    );

  return (
    <BottomSheet title={t("package.new")} onClose={onClose}>
      <Text accessibilityRole="header" style={[Type.heading, { color: c.ink, fontSize: 24 }]}>
        {t("package.new")}
      </Text>
      <Text style={[Type.small, { color: c.ink2 }]}>
        {studentName} · {t("package.boughtOn", { date: formatDay(today, locale) })}
      </Text>

      <Text style={[Type.small, { color: c.ink, fontFamily: Fonts.bodyBold }]}>{t("package.lessons")}</Text>
      <FilterChips
        role="radio"
        options={SIZES.map((n) => ({ id: String(n), label: String(n) }))}
        value={SIZES.some((n) => String(n) === lessons) ? lessons : null}
        onChange={setLessons}
      />
      <TextField label={t("package.otherSize")} value={lessons} onChangeText={setLessons} keyboardType="number-pad" maxLength={3} />
      <TextField label={t("package.price")} value={price} onChangeText={setPrice} keyboardType="decimal-pad" />

      <Text style={[Type.small, { color: c.ink, fontFamily: Fonts.bodyBold }]}>{t("package.expiry")}</Text>
      <FilterChips
        role="radio"
        options={[
          { id: "none", label: t("package.expiryNone") },
          { id: "3", label: t("package.expiryMonths", { count: "3" }) },
          { id: "6", label: t("package.expiryMonths", { count: "6" }) },
          { id: "12", label: t("package.expiryMonths", { count: "12" }) },
        ]}
        value={expiry}
        onChange={setExpiry}
      />

      <ErrorText error={create.error} />
      <Button title={t("common.save")} large block onPress={handleSave} loading={create.isPending} disabled={!ready} />
    </BottomSheet>
  );
}
