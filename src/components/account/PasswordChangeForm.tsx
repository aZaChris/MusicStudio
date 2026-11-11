import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Text, View } from "react-native";

import { Button } from "@/components/Button";
import { ErrorText } from "@/components/QueryState";
import { SectionTitle } from "@/components/Screen";
import { TextField } from "@/components/TextField";
import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";

/** Changing the password ends every session, this one included: the user signs in again. */
export function PasswordChangeForm() {
  const c = useTheme();
  const t = useT();
  const { logout } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const change = useMutation({
    mutationFn: () =>
      apiFetch("/auth/password/change/", { method: "POST", body: { current_password: current, new_password: next } }),
    onSuccess: () => logout(), // the server already revoked the tokens; this clears local state
  });

  return (
    <View style={{ gap: 14 }}>
      <SectionTitle>{t("account.changePassword")}</SectionTitle>
      <Text style={[Type.small, { color: c.ink2 }]}>{t("account.changePasswordHint")}</Text>
      <TextField label={t("account.currentPassword")} value={current} onChangeText={setCurrent} secureTextEntry autoComplete="password" />
      <TextField label={t("account.newPassword")} value={next} onChangeText={setNext} secureTextEntry autoComplete="new-password" />
      <ErrorText error={change.error} />
      <Button title={t("account.changePassword")} onPress={() => change.mutate()} loading={change.isPending} disabled={!current || !next} />
    </View>
  );
}
