// Turn any failure into a message the user can read, in their language (constitution I, VI).
import { ApiError } from "./api/client";
import type { Translate } from "./i18n";

export function errorMessage(error: unknown, t: Translate): string {
  if (!(error instanceof ApiError)) return t("error.unexpected");
  switch (error.status) {
    case 0:
      return t("error.network");
    case 401:
      return t("error.sessionExpired");
    case 403:
      return t("error.forbidden");
    case 404:
      return t("error.notFound");
    case 429:
      return t("error.rateLimited");
  }
  if (error.status >= 500) return t("error.server");
  // 400 / 409: the server says why. DRF field errors are shown as "field: message".
  const [field, messages] = Object.entries(error.fieldErrors)[0] ?? [];
  const reason =
    error.detail ?? (messages ? (field === "non_field_errors" ? messages[0] : `${field}: ${messages[0]}`) : undefined);
  return reason ? t("error.rejectedWithReason", { reason }) : t("error.rejected");
}

/** Errors that a retry cannot fix: the request itself was refused. */
export function isClientError(error: unknown): boolean {
  return error instanceof ApiError && error.status >= 400 && error.status < 500;
}
