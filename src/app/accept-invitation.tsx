import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { Text } from "react-native";

import { Alert } from "@/components/Alert";
import { Button } from "@/components/Button";
import { CheckField } from "@/components/CheckField";
import { ErrorText } from "@/components/QueryState";
import { Screen, ScreenHeader } from "@/components/Screen";
import { TextField } from "@/components/TextField";
import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { apiFetch, session } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";
import { tokenFrom } from "@/lib/invitation";

type Lookup = components["schemas"]["InvitationLookup"];

export default function AcceptInvitationScreen() {
  const c = useTheme();
  const t = useT();
  const router = useRouter();
  const { user, retry } = useAuth();
  const params = useLocalSearchParams<{ token?: string }>();
  const [pasted, setPasted] = useState("");
  const token = params.token ? tokenFrom(params.token) : tokenFrom(pasted);
  const [form, setForm] = useState({ first_name: "", last_name: "", password: "" });
  const [terms, setTerms] = useState(false);
  const [consent, setConsent] = useState(false);

  const lookup = useQuery({
    queryKey: ["invitation", token],
    queryFn: () => apiFetch<Lookup>(`/invitations/lookup/?token=${encodeURIComponent(token)}`, { auth: false }),
    enabled: token.length > 0,
    retry: false,
  });
  const accept = useMutation({
    mutationFn: () =>
      apiFetch<{ access: string; refresh: string }>("/invitations/accept/", {
        method: "POST",
        body: {
          token,
          ...(lookup.data?.existing_account ? {} : form),
          accept_terms: terms,
          consent: lookup.data?.role === "parent" ? consent : false,
        },
        auth: signedInAsInvitee, // an existing account accepts while signed in, without a password
      }),
    onSuccess: async (tokens) => {
      await session.start(tokens);
      retry(); // check who we are with the new session
      router.replace("/");
    },
  });

  const invitation = lookup.data;
  const isParent = invitation?.role === "parent";
  const signedInAsInvitee = !!invitation && user?.email.toLowerCase() === invitation.email.toLowerCase();

  return (
    <Screen>
      <ScreenHeader title={t("invitation.title")} right={<Button title={t("auth.backToLogin")} variant="ghost" onPress={() => router.replace("/login")} />} />
      {!params.token ? <TextField label={t("invitation.paste")} value={pasted} onChangeText={setPasted} autoCapitalize="none" /> : null}
      {lookup.isError ? <Alert kind="error">{t("invitation.invalid")}</Alert> : null}
      {invitation?.existing_account && !signedInAsInvitee ? (
        <>
          <Alert kind="warning">{t("invitation.existing", { email: invitation.email })}</Alert>
          <Button title={t("auth.login")} onPress={() => router.replace("/login")} />
        </>
      ) : null}
      {invitation && (!invitation.existing_account || signedInAsInvitee) ? (
        <>
          <Text style={[Type.body, { color: c.ink }]}>{t("invitation.hint", { studio: invitation.studio_name, role: t(`auth.role.${invitation.role as "teacher" | "parent" | "student"}`) })}</Text>
          {isParent && invitation.student_first_names.length > 0 ? (
            <Text style={[Type.small, { color: c.ink2 }]}>{t("invitation.forStudents", { names: invitation.student_first_names.join(", ") })}</Text>
          ) : null}
          {!invitation.existing_account ? (
            <>
          <TextField label={t("student.firstName")} value={form.first_name} onChangeText={(v) => setForm({ ...form, first_name: v })} autoCapitalize="words" />
          <TextField label={t("student.lastName")} value={form.last_name} onChangeText={(v) => setForm({ ...form, last_name: v })} autoCapitalize="words" />
          <TextField label={t("auth.password")} value={form.password} onChangeText={(v) => setForm({ ...form, password: v })} secureTextEntry autoComplete="new-password" />
            </>
          ) : null}
          <CheckField label={t("invitation.terms")} value={terms} onChange={setTerms} />
          {isParent ? <CheckField label={t("invitation.consent")} value={consent} onChange={setConsent} /> : null}
          <ErrorText error={accept.error} />
          <Button
            title={t("invitation.accept")}
            large
            block
            onPress={() => accept.mutate()}
            loading={accept.isPending}
            disabled={(!invitation.existing_account && (!form.first_name || !form.password)) || !terms || (isParent && !consent)}
          />
        </>
      ) : null}
    </Screen>
  );
}
