import { Redirect } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/Button";
import { TextField } from "@/components/TextField";
import { Fonts, Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";

export default function LoginScreen() {
  const theme = useTheme();
  const t = useT();
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (user) return <Redirect href="/" />;

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch {
      setError(t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.center}
      >
        <View style={styles.form}>
          <View style={styles.logo}>
            <View style={[styles.logoMark, { backgroundColor: theme.accent }]}>
              <Text style={styles.logoGlyph}>♪</Text>
            </View>
            <Text style={[styles.title, { color: theme.text }]}>MusicStudio</Text>
          </View>

          <TextField
            label={t("auth.email")}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
          />
          <TextField label={t("auth.password")} value={password} onChangeText={setPassword} secureTextEntry />

          {error && <Text style={{ color: theme.dangerText }}>{error}</Text>}

          <Button title={t("auth.login")} onPress={handleSubmit} loading={loading} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: Spacing.four },
  form: { width: "100%", maxWidth: 340, gap: Spacing.three },
  logo: { alignItems: "center", gap: Spacing.two, marginBottom: Spacing.two },
  logoMark: { width: 48, height: 48, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  logoGlyph: { color: "white", fontSize: 22 },
  title: { fontFamily: Fonts.headingBold, fontSize: 22 },
});
