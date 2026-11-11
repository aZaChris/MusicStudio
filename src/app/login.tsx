import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import Svg, { Ellipse, Line } from "react-native-svg";
import { SafeAreaView } from "react-native-safe-area-context";

import { Alert } from "@/components/Alert";
import { Button } from "@/components/Button";
import { LogoMark } from "@/components/Logo";
import { TextField } from "@/components/TextField";
import { Radii, shadow, Type } from "@/constants/theme";
import { useScheme, useTheme } from "@/hooks/use-theme";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useT } from "@/lib/i18n";

// Five staff lines with three notes: decoration only, never behind text that must be read.
const LINES = [10, 26, 42, 58, 74];
const NOTES = [
  [250, 58],
  [300, 42],
  [350, 26],
];

export default function LoginScreen() {
  const c = useTheme();
  const scheme = useScheme();
  const t = useT();
  const router = useRouter();
  const { user, notice, login, verifyMfa } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [unconfirmed, setUnconfirmed] = useState(false);
  const [resent, setResent] = useState(false);

  if (user) return <Redirect href="/" />;

  const handleSubmit = async () => {
    setError(null);
    setUnconfirmed(false);
    setLoading(true);
    try {
      if (mfaToken) {
        await verifyMfa(mfaToken, code);
        return;
      }
      const result = await login(email, password);
      if (result.mfaToken) setMfaToken(result.mfaToken);
    } catch (err) {
      if (err instanceof ApiError && err.code === "email_not_confirmed") {
        setUnconfirmed(true); // the server says so only after a correct password
      } else if (mfaToken && err instanceof ApiError && err.status === 401) {
        setError(t("auth.mfaInvalid"));
      } else {
        // 401 on login = wrong credentials; anything else (offline, throttled) says what it is.
        setError(err instanceof ApiError && err.status === 401 ? t("auth.invalidCredentials") : errorMessage(err, t));
      }
    } finally {
      setLoading(false);
    }
  };

  const resend = async () => {
    try {
      await apiFetch("/auth/confirm-email/resend/", { method: "POST", body: { email }, auth: false });
      setResent(true);
    } catch (err) {
      setError(errorMessage(err, t));
    }
  };

  return (
    <View style={[styles.fill, { backgroundColor: c.paper }]}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.fill}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled" bounces={false}>
          <SafeAreaView edges={["top"]} style={[styles.story, { backgroundColor: c.plum }]}>
            <Svg width="100%" height={90} viewBox="0 0 390 90" preserveAspectRatio="none" style={styles.staff} accessible={false}>
              {LINES.map((y) => (
                <Line key={y} x1="0" y1={y} x2="390" y2={y} stroke={c.plumLine} strokeWidth={1.5} />
              ))}
              {NOTES.map(([cx, cy]) => (
                <Ellipse key={cx} cx={cx} cy={cy} rx="9" ry="7" fill={c.orange} rotation={-20} originX={cx} originY={cy} />
              ))}
            </Svg>
            <LogoMark size={52} />
            <Text accessibilityRole="header" style={[Type.titleXl, { color: c.onPlum }]}>
              {t("auth.heroTitle")}
            </Text>
            <Text style={[Type.body, { color: c.plumSoft }]}>{t("auth.heroText")}</Text>
          </SafeAreaView>

          <View style={[styles.form, { backgroundColor: c.card }, shadow("card", scheme)]}>
            {mfaToken ? (
              <TextField
                label={t("auth.mfaCode")}
                value={code}
                onChangeText={setCode}
                autoCapitalize="none"
                autoComplete="one-time-code"
              />
            ) : (
              <>
                <TextField
                  label={t("auth.email")}
                  value={email}
                  onChangeText={setEmail}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  autoComplete="email"
                  textContentType="username"
                />
                <TextField
                  label={t("auth.password")}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  autoComplete="password"
                  textContentType="password"
                />
              </>
            )}
            <Button title={t("auth.login")} large block onPress={handleSubmit} loading={loading} />
            {unconfirmed ? (
              <Alert kind="warning">{resent ? t("auth.confirmationSent") : t("auth.notConfirmed")}</Alert>
            ) : null}
            {unconfirmed && !resent ? <Button title={t("auth.resendConfirmation")} variant="secondary" onPress={resend} /> : null}
            {notice && !error ? <Alert kind="warning">{t(notice)}</Alert> : null}
            {error ? <Alert kind="error">{error}</Alert> : null}
            {!mfaToken ? (
              <>
                <Button title={t("auth.forgotPassword")} variant="ghost" onPress={() => router.push("/forgot-password")} />
                <Button title={t("invitation.have")} variant="ghost" onPress={() => router.push("/accept-invitation")} />
              </>
            ) : null}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  scroll: { flexGrow: 1 },
  story: { minHeight: 340, paddingHorizontal: 28, paddingTop: 24, paddingBottom: 72, gap: 14 },
  staff: { position: "absolute", left: 0, right: 0, bottom: 56 },
  form: { marginTop: -40, marginHorizontal: 20, marginBottom: 32, borderRadius: Radii.sheet, padding: 22, gap: 18 },
});
