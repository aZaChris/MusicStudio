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

/**
 * A wall-clock date + time picked by the user ("2026-11-12", "16:30") as the instant the API
 * stores. Built from the phone's local time, so 16:30 in Rome stays 16:30 across summer time.
 */
export function localDateTimeToISO(day: string, time: string): string {
  const [y, m, d] = day.split("-").map(Number);
  const [hh, mm] = time.split(":").map(Number);
  return new Date(y, m - 1, d, hh, mm).toISOString();
}

/** The next `count` calendar days from `from`, as API dates (`YYYY-MM-DD`), today first. */
export function nextDays(count: number, from: Date = new Date()): string[] {
  return Array.from({ length: count }, (_, i) => localDateISO(new Date(from.getFullYear(), from.getMonth(), from.getDate() + i)));
}

/** `date` plus whole months, as an API date. A 31st lands on the last day of a shorter month. */
export function addMonths(day: string, months: number): string {
  const [y, m, d] = day.split("-").map(Number);
  const target = new Date(y, m - 1 + months, 1);
  const last = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate();
  return localDateISO(new Date(target.getFullYear(), target.getMonth(), Math.min(d, last)));
}
