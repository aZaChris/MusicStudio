import { expect, test } from 'vitest'

import { formatDay, localDateISO } from './dates'

// Tests run with TZ=Europe/Rome (package.json), like the portal's users.
test('just after midnight in Rome the local date is today, while UTC is still yesterday', () => {
  const halfPastMidnight = new Date(2026, 10, 10, 0, 30)
  expect(halfPastMidnight.toISOString().slice(0, 10)).toBe('2026-11-09') // the old bug
  expect(localDateISO(halfPastMidnight)).toBe('2026-11-10')
})

test('a calendar date is shown as that same day', () => {
  expect(formatDay('2026-11-09', 'en-GB')).toBe('9 Nov 2026')
})
