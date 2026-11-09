import type { ReactNode } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { Spacing } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { errorMessage } from "@/lib/errors";
import { useT } from "@/lib/i18n";
import { Button } from "./Button";

interface QueryLike {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

/**
 * One way to show loading, failure and "nothing here" on every screen, so no screen is ever
 * silently blank (audit issue 9).
 */
export function QueryState({
  query,
  isEmpty = false,
  emptyText,
  children,
}: {
  query: QueryLike;
  isEmpty?: boolean;
  emptyText?: string;
  children: ReactNode;
}) {
  const theme = useTheme();
  const t = useT();

  if (query.isPending) {
    return (
      <View style={styles.center} accessibilityLabel={t("common.loading")}>
        <ActivityIndicator />
      </View>
    );
  }
  if (query.isError) {
    return (
      <View style={styles.center}>
        <Text accessibilityRole="alert" style={[styles.text, { color: theme.dangerText }]}>
          {errorMessage(query.error, t)}
        </Text>
        <Button title={t("common.retry")} variant="secondary" onPress={() => query.refetch()} />
      </View>
    );
  }
  if (isEmpty) {
    return <Text style={[styles.text, { color: theme.textSecondary }]}>{emptyText}</Text>;
  }
  return <>{children}</>;
}

/** Inline error for forms and dialogs. */
export function ErrorText({ error }: { error: unknown }) {
  const theme = useTheme();
  const t = useT();
  if (!error) return null;
  return (
    <Text accessibilityRole="alert" style={{ color: theme.dangerText }}>
      {errorMessage(error, t)}
    </Text>
  );
}

const styles = StyleSheet.create({
  center: { padding: Spacing.four, alignItems: "center", gap: Spacing.three },
  text: { textAlign: "center" },
});
