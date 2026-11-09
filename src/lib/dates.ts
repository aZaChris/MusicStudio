// Dates in the device's time zone. Never `toISOString().slice(0, 10)` for a local date:
// that is the UTC date, which is still "yesterday" after midnight in Italy (audit issue 7).
import type { Locale } from "./i18n";

const pad = (n: number) => String(n).padStart(2, "0");

/** Today's (or `date`'s) calendar date in local time, as the API's `YYYY-MM-DD`. */
export function localDateISO(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

const tag = (locale: Locale) => (locale === "it" ? "it-IT" : "en-GB");

/** A lesson start (`date-time` from the API) shown in local time, e.g. "Mon 9 Nov, 15:00". */
export function formatDateTime(iso: string, locale: Locale): string {
  return new Date(iso).toLocaleString(tag(locale), {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * A calendar date (`date` from the API, "YYYY-MM-DD"). Parsed as local midnight on purpose:
 * `new Date("2026-11-09")` is UTC midnight, which is the 8th in any time zone west of UTC.
 */
export function formatDay(day: string, locale: Locale): string {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(tag(locale), {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** A `date-time` shown as its local calendar day. */
export function formatDateOfDateTime(iso: string, locale: Locale): string {
  return formatDay(localDateISO(new Date(iso)), locale);
}
