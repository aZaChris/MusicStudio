import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Linking, Text, View } from "react-native";

import { Alert } from "@/components/Alert";
import { Button } from "@/components/Button";
import { ErrorText, QueryState } from "@/components/QueryState";
import { SectionTitle } from "@/components/Screen";
import { TextField } from "@/components/TextField";
import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { apiFetch } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useT } from "@/lib/i18n";

type Status = components["schemas"]["MfaStatus"];
type Setup = components["schemas"]["MfaSetup"];
type Codes = components["schemas"]["MfaRecoveryCodes"];

/** Two-step verification for owners and teachers: set up, see recovery codes once, turn off. */
export function MfaPanel() {
  const c = useTheme();
  const t = useT();
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: ["mfa"], queryFn: () => apiFetch<Status>("/auth/mfa/") });
  const [setup, setSetup] = useState<Setup | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null); // shown once, never stored
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["mfa"] });
  const reset = () => {
    setCode("");
    setPassword("");
  };

  const start = useMutation({
    mutationFn: () => apiFetch<Setup>("/auth/mfa/setup/", { method: "POST" }),
    onSuccess: setSetup,
  });
  const confirm = useMutation({
    mutationFn: () => apiFetch<Codes>("/auth/mfa/confirm/", { method: "POST", body: { code } }),
    onSuccess: (res) => {
      setCodes(res.recovery_codes);
      setSetup(null);
      reset();
      void refresh();
    },
  });
  const disable = useMutation({
    mutationFn: () => apiFetch("/auth/mfa/disable/", { method: "POST", body: { password, code } }),
    onSuccess: () => {
      reset();
      void refresh();
    },
  });
  const regenerate = useMutation({
    mutationFn: () => apiFetch<Codes>("/auth/mfa/recovery-codes/", { method: "POST", body: { password, code } }),
    onSuccess: (res) => {
      setCodes(res.recovery_codes);
      reset();
      void refresh();
    },
  });

  const codeField = <TextField label={t("auth.mfaCode")} value={code} onChangeText={setCode} autoCapitalize="none" autoComplete="one-time-code" />;

  return (
    <View style={{ gap: 14 }}>
      <SectionTitle>{t("mfa.title")}</SectionTitle>
      <QueryState query={status}>
        {codes ? (
          <View style={{ gap: 8 }}>
            <Alert kind="warning">{`${t("mfa.recoveryTitle")}. ${t("mfa.recoveryHint")}`}</Alert>
            {codes.map((item) => (
              <Text key={item} selectable style={[Type.body, { color: c.ink, fontVariant: ["tabular-nums"] }]}>
                {item}
              </Text>
            ))}
            <Button title={t("mfa.savedCodes")} variant="secondary" onPress={() => setCodes(null)} />
          </View>
        ) : null}

        {!status.data?.enabled && !setup ? (
          <View style={{ gap: 10 }}>
            <Text style={[Type.small, { color: c.ink2 }]}>{t("mfa.off")}</Text>
            <Button title={t("mfa.enable")} onPress={() => start.mutate()} loading={start.isPending} />
            <ErrorText error={start.error} />
          </View>
        ) : null}

        {setup ? (
          <View style={{ gap: 12 }}>
            <Text style={[Type.body, { color: c.ink }]}>{t("mfa.setupHint")}</Text>
            <Text selectable accessibilityLabel={t("mfa.secret")} style={[Type.body, { color: c.ink }]}>
              {setup.secret}
            </Text>
            <Button title={t("mfa.openApp")} variant="ghost" onPress={() => void Linking.openURL(setup.otpauth_uri)} />
            {codeField}
            <ErrorText error={confirm.error} />
            <Button title={t("mfa.confirm")} onPress={() => confirm.mutate()} loading={confirm.isPending} disabled={!code} />
          </View>
        ) : null}

        {status.data?.enabled ? (
          <View style={{ gap: 12 }}>
            <Text style={[Type.body, { color: c.ink }]}>{t("mfa.on", { count: String(status.data.recovery_codes_left) })}</Text>
            <TextField label={t("auth.password")} value={password} onChangeText={setPassword} secureTextEntry autoComplete="password" />
            {codeField}
            <ErrorText error={disable.error ?? regenerate.error} />
            <Button title={t("mfa.newCodes")} variant="secondary" onPress={() => regenerate.mutate()} disabled={!password || !code} />
            <Button title={t("mfa.disable")} variant="secondary" onPress={() => disable.mutate()} disabled={!password || !code} />
          </View>
        ) : null}
      </QueryState>
    </View>
  );
}
