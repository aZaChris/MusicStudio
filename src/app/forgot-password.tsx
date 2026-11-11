import { useMutation } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Text } from "react-native";

import { Alert } from "@/components/Alert";
import { Button } from "@/components/Button";
import { ErrorText } from "@/components/QueryState";
import { Screen, ScreenHeader } from "@/components/Screen";
import { TextField } from "@/components/TextField";
import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { apiFetch } from "@/lib/api/client";
import { useT } from "@/lib/i18n";

/** Always the same answer, so the screen never reveals whether an address is registered. */
export default function ForgotPasswordScreen() {
  const c = useTheme();
  const t = useT();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const send = useMutation({
    mutationFn: () => apiFetch("/auth/password-reset/", { method: "POST", body: { email }, auth: false }),
  });

  return (
    <Screen>
      <ScreenHeader title={t("forgot.title")} right={<Button title={t("auth.backToLogin")} variant="ghost" onPress={() => router.replace("/login")} />} />
      <Text style={[Type.body, { color: c.ink2 }]}>{t("forgot.hint")}</Text>
      {send.isSuccess ? (
        <Alert kind="success">{t("forgot.sent")}</Alert>
      ) : (
        <>
          <TextField label={t("auth.email")} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
          <ErrorText error={send.error} />
          <Button title={t("forgot.submit")} large block onPress={() => send.mutate()} loading={send.isPending} disabled={!email} />
        </>
      )}
    </Screen>
  );
}
