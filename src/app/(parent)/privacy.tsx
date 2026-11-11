import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Share, Text, View } from "react-native";

import { Alert } from "@/components/Alert";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { CheckField } from "@/components/CheckField";
import { ErrorText, QueryState } from "@/components/QueryState";
import { Screen, ScreenHeader, SectionTitle } from "@/components/Screen";
import { TextField } from "@/components/TextField";
import { PasswordChangeForm } from "@/components/account/PasswordChangeForm";
import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { apiFetch } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth-context";
import { formatDay } from "@/lib/dates";
import { useLocale, useT } from "@/lib/i18n";

type Consent = components["schemas"]["Consent"];

/** Parents and adult students: consents, a copy of their data, and closing the account. */
export default function PrivacyScreen() {
  const c = useTheme();
  const t = useT();
  const locale = useLocale();
  const router = useRouter();
  const { logout } = useAuth();
  const queryClient = useQueryClient();
  const consents = useQuery({ queryKey: ["consents"], queryFn: () => apiFetch<Consent[]>("/privacy/consents/") });
  const [password, setPassword] = useState("");
  const [understood, setUnderstood] = useState(false);

  const download = useMutation({
    mutationFn: () => apiFetch<unknown>("/privacy/export/"),
    // The system share sheet: save to Files, send by email... The file never touches our storage.
    onSuccess: (data) => Share.share({ message: JSON.stringify(data, null, 2), title: "musicstudio-export.json" }),
  });
  const withdraw = useMutation({
    mutationFn: (id: number) => apiFetch(`/privacy/consents/${id}/withdraw/`, { method: "POST", body: { password } }),
    onSuccess: () => {
      setPassword("");
      void queryClient.invalidateQueries(); // the children are gone from the lists
    },
  });
  const erase = useMutation({
    mutationFn: () => apiFetch("/privacy/erase/", { method: "POST", body: { password } }),
    onSuccess: () => logout(),
  });

  return (
    <Screen>
      <ScreenHeader title={t("privacy.title")} right={<Button title={t("privacy.back")} variant="ghost" onPress={() => router.back()} />} />

      <SectionTitle>{t("privacy.consents")}</SectionTitle>
      <QueryState query={consents} isEmpty={consents.data?.length === 0} emptyText={t("privacy.noConsents")}>
        {consents.data?.map((item) => (
          <Card key={item.id} row style={{ gap: 6 }}>
            <Text style={[Type.heading, { color: c.ink, fontSize: 17 }]}>{item.children.map((child) => child.name).join(", ")}</Text>
            <Text style={[Type.small, { color: c.ink2 }]}>
              {t("privacy.givenOn", { date: formatDay(item.given_at, locale), version: item.notice_version })}
            </Text>
            {item.withdrawn_at ? (
              <Text style={[Type.small, { color: c.ink2 }]}>{t("privacy.withdrawn")}</Text>
            ) : (
              <Button title={t("privacy.withdraw")} variant="secondary" disabled={!password} onPress={() => withdraw.mutate(item.id)} />
            )}
          </Card>
        ))}
      </QueryState>
      <ErrorText error={withdraw.error} />

      <SectionTitle>{t("privacy.exportTitle")}</SectionTitle>
      <Text style={[Type.small, { color: c.ink2 }]}>{t("privacy.exportHint")}</Text>
      <Button title={t("privacy.download")} variant="secondary" onPress={() => download.mutate()} loading={download.isPending} />
      <ErrorText error={download.error} />

      <SectionTitle>{t("privacy.eraseTitle")}</SectionTitle>
      <Alert kind="warning">{t("privacy.eraseWarning")}</Alert>
      <TextField label={t("privacy.passwordToConfirm")} value={password} onChangeText={setPassword} secureTextEntry autoComplete="password" />
      <CheckField label={t("privacy.eraseConfirm")} value={understood} onChange={setUnderstood} />
      <ErrorText error={erase.error} />
      <Button title={t("privacy.erase")} onPress={() => erase.mutate()} loading={erase.isPending} disabled={!password || !understood} />

      <View style={{ height: 8 }} />
      <PasswordChangeForm />
    </Screen>
  );
}
