// Dates in the browser's time zone. Never `toISOString().slice(0, 10)` for a local date:
// that is the UTC date, still "yesterday" after midnight in Italy.
const pad = (n: number) => String(n).padStart(2, '0')

// Day-month order for English too: the product is Italian, "9 Nov" reads better than "Nov 9".
const tag = (language: string) => (language.startsWith('it') ? 'it-IT' : 'en-GB')

/** Today's (or `date`'s) local calendar date, as the API's `YYYY-MM-DD`. */
export function localDateISO(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** A `date` from the API ("YYYY-MM-DD") parsed as local midnight, not UTC midnight. */
export function formatDay(day: string, locale: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(tag(locale), {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** A `date-time` from the API shown in local time. */
export function formatDateTime(iso: string, locale: string): string {
  return new Date(iso).toLocaleString(tag(locale), {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTime(iso: string, locale: string): string {
  return new Date(iso).toLocaleTimeString(tag(locale), { hour: '2-digit', minute: '2-digit' })
}

/**
 * A wall-clock date + time typed by the user ("2026-11-12", "16:30") as the instant the API
 * stores. Built from the browser's local time, so 16:30 in Rome stays 16:30 in Rome all year,
 * summer time included.
 */
export function localDateTimeToISO(day: string, time: string): string {
  const [y, m, d] = day.split('-').map(Number)
  const [hh, mm] = time.split(':').map(Number)
  return new Date(y, m - 1, d, hh, mm).toISOString()
}
