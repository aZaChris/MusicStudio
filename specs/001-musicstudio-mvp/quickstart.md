# Quickstart: validate MusicStudio MVP end-to-end

> **Amended 2026-09-17**: rebuilt on Next.js/Vercel (see research.md). Local dev no longer
> needs Docker Compose — just Node.js and a Postgres connection string (local or a Neon branch).

## Status of this environment

Verified from this session so far: `npm run build` (clean), `npx tsc --noEmit` (clean),
`npx oxlint`-equivalent lint clean. **Not yet run**: `vitest` (needs a real
`DATABASE_URL` — waiting on the Neon Marketplace terms-acceptance step, or point at a local
Postgres instance), the actual browser walkthrough below.

## Prerequisites

- Node.js 22, this repo's `npm install` already run.
- `vercel link` done, Neon Postgres provisioned via `vercel integration add neon` (accept the
  marketplace terms in the browser when prompted — the CLI can't do this step for you).
- `vercel env pull .env.local --yes` to get `DATABASE_URL` locally.
- `AUTH_SECRET` in `.env.local` (generate with `npx auth secret`).
- `CRON_SECRET` in `.env.local` (any random string) — only needed to hit
  `/api/cron/reminders` manually; Vercel injects it automatically on the deployed cron trigger.

## Bring the stack up

```bash
npm run db:push   # applies lib/db/schema.ts to the Neon database
npm run seed      # demo teachers/studio/students/packages/lessons/payments/parent
npm run dev       # http://localhost:3000
```

`scripts/seed.ts` creates: a solo teacher, a studio_owner with 2 teachers, students with
packages (one at 1 lesson remaining, to exercise the low-package warning), one parent linked to
that low-package student, one lesson today (for the completion demo), and one lesson ~24h out
(for the reminder demo). All demo logins use password `password123`.

## Validate User Story 1 — teacher week + lesson completion (spec.md US1)

1. Log in at `http://localhost:3000` as `solo.teacher@example.com`.
2. Confirm the dashboard shows this week's calendar, upcoming lessons, pending payments count,
   active students count.
3. Click today's lesson, add a note, mark it complete.
4. Confirm the student's package "lessons remaining" decreased by 1 (visible on `/students`).
5. Click the same (now completed) lesson again — it's disabled/non-clickable, confirming the
   UI can't double-submit; `markLessonCompleted`'s guarded UPDATE makes a direct API retry
   idempotent too.

## Validate User Story 2 — roster, student detail, payments (spec.md US2)

1. Open `/students` — confirm each row shows package/remaining/payment status, and the
   low-package student is flagged.
2. Open that student's detail page — confirm lesson history and package are visible.
3. Go to `/payments`, register a payment — confirm it appears in the list.

## Validate User Story 3 — parent portal isolation (spec.md US3)

1. Log in (separate browser/session) as `parent@example.com`.
2. Confirm `/parent` shows only the linked student's data, no edit controls anywhere.
3. Attempt to fetch another student's data directly: `curl -b <session-cookie>
   http://localhost:3000/api/v1/students/{other_student_id}` — confirm `404`, not the other
   student's data.
4. Confirm the lesson completed in US1, with its note, is visible read-only here.

## Validate User Story 4 — reminders (spec.md US4)

1. Manually trigger the sweep: `curl -H "Authorization: Bearer $CRON_SECRET"
   http://localhost:3000/api/cron/reminders`.
2. Confirm the response is `{"sent":1}` (or more) and check the terminal running `npm run dev`
   for the logged reminder email (console-logged for MVP — see research.md).
3. Re-run the same curl — confirm `{"sent":0}` (idempotent, `reminderSentAt` already stamped).

## API surface check

- Every route in `contracts/api.md` should return `401` unauthenticated, and the expected
  shape/status once logged in (session cookie via `/api/auth/callback/credentials`).

## Automated test suite

```bash
npm run test   # tests/*.test.ts — package decrement, permission scoping, payment
               # validation, reminder sweep, all against a real Postgres DB
```
