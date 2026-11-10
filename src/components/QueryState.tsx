import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Type } from "@/constants/theme";
import { useTheme } from "@/hooks/use-theme";
import { errorMessage } from "@/lib/errors";
import { useT } from "@/lib/i18n";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Skeleton } from "./Skeleton";

interface QueryLike {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

/**
 * One way to show loading, failure and "nothing here" on every screen, so no screen is ever
 * silently blank (audit issue 9). Loading is list-shaped placeholders, not a spinner.
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
  const c = useTheme();
  const t = useT();

  if (query.isPending) {
    return (
      <View style={styles.stack} accessibilityLabel={t("common.loading")} accessibilityRole="progressbar">
        <Skeleton />
        <Skeleton />
        <Skeleton />
      </View>
    );
  }
  if (query.isError) {
    return (
      <View style={styles.stack}>
        <Alert kind="error">{errorMessage(query.error, t)}</Alert>
        <Button title={t("common.retry")} variant="secondary" onPress={() => query.refetch()} />
      </View>
    );
  }
  if (isEmpty) {
    return <Text style={[Type.small, { color: c.ink2 }]}>{emptyText}</Text>;
  }
  return <>{children}</>;
}

/** Inline error for forms and sheets. */
export function ErrorText({ error }: { error: unknown }) {
  const t = useT();
  if (!error) return null;
  return <Alert kind="error">{errorMessage(error, t)}</Alert>;
}

const styles = StyleSheet.create({ stack: { gap: 12 } });
