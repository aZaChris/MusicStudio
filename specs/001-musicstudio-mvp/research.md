# Phase 0 Research: MusicStudio MVP

> **Amended 2026-09-17**: the original version of this document researched a Django/DRF +
> Celery/Docker/AWS stack. The user decided mid-build to run everything on Vercel instead; that
> version is preserved in git history (commits before "Drop Django/Vite/Docker stack..."). This
> is the research behind the Next.js/Vercel rebuild.

## Why one Next.js app instead of separate frontend/backend services

- **Decision**: a single Next.js (App Router) project — Server Components/Server Actions serve
  the web UI, Route Handlers under `/api/v1/` serve the documented REST API for a future mobile
  client, both calling the same `lib/services/*` business logic.
- **Rationale**: this is Vercel's idiomatic shape for "frontend and backend deployed together"
  (per the platform's own guidance: prefer Next.js Route Handlers when the backend belongs to a
  Next.js app). Using Vercel Services (separate frontend+backend components in one deployment)
  or a separate Express/Hono backend would add a second framework and a second deploy artifact
  for no benefit at this scale.
- **Alternatives considered**: Vercel Services with a standalone Hono/Express API — rejected,
  unnecessary indirection for a single small team/product; Next.js Route Handlers alone (no
  Server Components for the web UI, treating it like a pure SPA) — rejected, throws away
  Next.js's actual strength (direct server-side data access, no client-side waterfall) for no
  reason since we're already committed to Next.js.

## Auth & multi-role access

- **Decision**: `users` table with a `role` column (`teacher | studio_owner | parent`) and a
  bcrypt `password_hash`; Auth.js (`next-auth` v5) with the Credentials provider and JWT session
  strategy (no DB session table — sessions are self-contained JWTs, simplest with a serverless
  Postgres backend). `studio_owner` is a `teachers` row with `is_owner=true` rather than a
  fourth table, same reasoning as the original design (an owner always has their own teaching
  practice too).
- **Rationale**: our accounts are invite-only (a teacher/admin provisions parent accounts) with
  three fixed custom roles baked into every authorization check — this is a poor fit for a
  social-login-oriented SaaS auth vendor (Clerk/Descope/Auth0), which optimizes for public
  self-signup and stores custom roles as bolted-on metadata. A Credentials provider against our
  own `users` table keeps the RBAC model exactly where the rest of the business logic already
  lives, with zero new third-party dependency or cost.
- **Alternatives considered**: Clerk (Vercel Marketplace-native, fastest setup for typical
  SaaS auth) — rejected for this app's shape (see above), revisit if the product ever grows
  public self-signup or SSO requirements.

## Tenant isolation enforcement

- **Decision**: `lib/rbac.ts` exports per-entity `*Scope(actor)` functions
  (`studentScope`, `lessonScope`, `packageScope`, `paymentScope`) returning a Drizzle `SQL`
  condition built from the actor's role/teacherId/studioId/parentAccountId, applied via
  `.where(and(scope(actor), ...))` in every service-layer query. A `getActor()` helper resolves
  the JWT's `userId`/`role` into the actor's linked teacher/parent profile on each request.
- **Rationale**: same principle as the original Django design (queryset-level filtering, never
  serializer-level hiding), translated to Drizzle: a SQL condition builder is the direct
  TypeScript equivalent of `get_queryset()` overrides, and keeping it in one file makes it the
  single reviewable choke point Constitution Principle I requires.
- **Alternatives considered**: row-level security (Postgres RLS) — appealing in principle, but
  would require session-scoped role variables per request against a serverless/pooled
  connection, adding real operational complexity for a 3-role, small-scale app; the query-scope
  functions get the same guarantee with a normal test suite.

## Package decrement correctness

- **Decision**: `markLessonCompleted` issues one guarded, atomic UPDATE:
  `UPDATE lessons SET status='completed', notes=$note WHERE id=$id AND status != 'completed'
  RETURNING *`. If it affects 0 rows (already completed, or outside the actor's scope), it's a
  no-op — idempotent by construction. Only if it *did* transition does a second guarded UPDATE
  run: `UPDATE packages SET lessons_remaining = lessons_remaining - 1 WHERE id=$id AND
  lessons_remaining > 0`.
- **Rationale**: a single conditional `UPDATE ... WHERE ... RETURNING` is an atomic
  compare-and-swap at the database level — race-safe against concurrent requests without an
  explicit transaction or row lock, and works identically over a pooled Postgres connection.
  This is simpler than the original Django design's `select_for_update()` + explicit
  transaction, while giving the same guarantee.
- **Alternatives considered**: wrapping both UPDATEs in an explicit transaction with
  `SELECT ... FOR UPDATE` — unnecessary here since each UPDATE's own `WHERE` guard is
  sufficient; a transaction would only be needed if the two statements had to succeed/fail
  together, but a lesson marked completed with a package decrement that doesn't (extremely
  unlikely, single-process failure between two adjacent statements) is an acceptable, self-
  healing edge case for an MVP, not a correctness bug.

## Background reminders

- **Decision**: a Vercel Cron Job (`vercel.json`, `*/15 * * * *`) hits
  `GET /api/cron/reminders` (protected by a `CRON_SECRET` bearer token), which runs
  `sendLessonReminders()`: queries `scheduled` lessons with `start_time` in the
  23h45m–24h window and `reminder_sent_at IS NULL`, sends one email per linked parent, and
  stamps `reminder_sent_at` for idempotency.
- **Rationale**: the only "background job" this MVP needs is a periodic, idempotent sweep — not
  a job queue with retries/fan-out. Vercel Cron Jobs are the direct platform-native fit and
  remove Celery + Redis entirely (no broker/worker to run or pay for).
- **Alternatives considered**: Vercel Queues / Workflow — rejected, both solve durable
  multi-step or fan-out job problems this MVP doesn't have; a scheduled HTTP endpoint is the
  smaller, correct-for-scope tool. Per-lesson scheduled Cron triggers (one job per lesson) —
  rejected, same reasoning as the original design: requires rescheduling on every edit/cancel,
  a periodic sweep is simpler and self-healing.
- **Email transport for MVP**: `console.log` (visible in Vercel function logs) — no
  transactional-email provider wired yet; swap `lib/services/email.ts`'s `sendEmail()` for a
  Marketplace provider (Resend, etc.) when real delivery is needed. The requirement is
  "demonstrably queued/sent," not deliverability at scale.

## Database driver: node-postgres, not the Neon serverless HTTP driver

- **Decision**: `drizzle-orm/node-postgres` + `pg.Pool`, pointed at Neon's connection string in
  production and local Postgres in tests — not `@neondatabase/serverless`'s HTTP/WebSocket
  transport.
- **Rationale**: this app runs on the Node.js runtime (Fluid Compute), not Edge, so there's no
  need for a fetch-based transport designed to work where raw TCP isn't available. Using plain
  `pg` means the exact same driver and code path run in Vitest (against local Postgres) and in
  production (against Neon) — no test-only DB shim, no build-time-safety workaround the
  `neon()` HTTP client needs. Neon is wire-compatible Postgres, so this is a fully supported
  path; Neon's pooled connection string (`-pooler` host) keeps this serverless-friendly despite
  using persistent-style TCP connections.
- **Alternatives considered**: `@neondatabase/serverless` (`neon-http` driver) — the
  Vercel-storage skill's preferred default, genuinely better if this ran on Edge or needed
  per-request HTTP fetch semantics; rejected here specifically because it blocked local testing
  against a real database (Constitution Principle III) without a Neon branch per test run, and
  this app's Node.js-runtime choice removes its main advantage.

## Frontend data & i18n

- **Decision**: Server Components fetch directly via `lib/services/*` (no client-side REST
  round-trip for the web UI itself); mutations go through Server Actions
  (`app/actions/*.ts`) calling the same services, with `revalidatePath()` for cache
  invalidation. i18n is a ~40-key dictionary in `lib/i18n.ts` (client-safe, pure) plus a
  server-only `getLocale()` cookie reader — no i18n library.
- **Rationale**: this is Next.js's own preferred pattern (avoids a redundant HTTP hop the old
  SPA needed) and the string surface is small and fixed enough that `react-i18next`/`next-intl`
  would be pure overhead for what a 40-entry object handles directly.
- **Alternatives considered**: `next-intl` — solid library, rejected as unneeded weight for a
  bilingual dictionary this small; TanStack Query on the client — rejected for the same reason
  Server Components are preferred: no client-side fetch needed when the server can just render
  the data.

## Theming

- **Decision**: unchanged from the original design — CSS custom properties from
  `design/tokens.md`, flipped under `:root[data-theme="dark"]`. The root layout reads a
  `musicstudio-theme` cookie server-side to set the initial `data-theme` attribute (avoids a
  flash of the wrong theme); a small client `ThemeToggle` component flips the attribute and the
  cookie together.

## Deployment

- **Decision**: one Vercel project (`vercel link`), Neon Postgres provisioned via the Vercel
  Marketplace (`vercel integration add neon`), `vercel.json` for the cron schedule. No
  Docker/AWS deliverable — deployment IS `git push` to the linked repo (or `vercel deploy`).
- **Rationale**: this is what the user explicitly asked to change; matches the platform's
  actual model (Vercel builds and deploys the Next.js app directly, no container step needed
  for a supported framework).
