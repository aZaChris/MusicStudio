// Register periods: a day, a month or a custom range, always as local calendar dates
// ("YYYY-MM-DD"), the same dates the API filters on (Europe/Rome).
export interface Period {
  from: string
  to: string
}

const pad = (n: number) => String(n).padStart(2, '0')

/** "2026-11" → 1 to 30 November. Built from local calendar parts, never from UTC. */
export function monthPeriod(yearMonth: string): Period {
  const [y, m] = yearMonth.split('-').map(Number)
  const last = new Date(y, m, 0).getDate() // day 0 of next month = last day of this one
  return { from: `${y}-${pad(m)}-01`, to: `${y}-${pad(m)}-${pad(last)}` }
}

export function dayPeriod(day: string): Period {
  return { from: day, to: day }
}

/** Longest period an export accepts (the server refuses more with `period_too_long`). */
export const MAX_EXPORT_DAYS = 366

const toUtcDay = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number)
  return Date.UTC(y, m - 1, d) / 86_400_000
}

/** Days covered, both ends included. Calendar arithmetic in UTC only to avoid DST hours. */
export function periodDays(p: Period): number {
  return toUtcDay(p.to) - toUtcDay(p.from) + 1
}

export const isValidPeriod = (p: Period) => Boolean(p.from) && Boolean(p.to) && p.from <= p.to
export const isExportable = (p: Period) => isValidPeriod(p) && periodDays(p) <= MAX_EXPORT_DAYS
