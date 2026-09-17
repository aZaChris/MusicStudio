# MusicStudio

A web platform for private music teachers and small studios (1-10 teachers) to manage
students, recurring lessons, lesson packages, payments, and parent communication —
replacing a patchwork of Calendly + spreadsheets + WhatsApp.

Built spec-first with [spec-kit](https://github.com/github/spec-kit); the full spec, plan,
research, data model, API contracts, and task history live in
[`specs/001-musicstudio-mvp/`](specs/001-musicstudio-mvp/). Project principles (tenant
isolation, API-first, test-first on business logic, MVP scope discipline) are in
[`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Stack

Everything runs on Vercel as one Next.js (App Router, TypeScript) app:

- **UI**: Server Components (reads) + Server Actions (mutations), role-scoped
  (teacher/studio_owner vs. parent), bilingual (EN/IT) with a light/dark theme toggle matching
  the design reference in `design/`.
- **API**: `/api/v1/*` Route Handlers exposing the same business logic as a documented REST
  surface, for a future React Native app (see the constitution's Principle II).
- **Data**: Drizzle ORM + Neon Postgres (Vercel Marketplace).
- **Auth**: Auth.js (Credentials provider, JWT sessions) against our own `users` table —
  accounts are invite-only, not public self-signup, so a custom-role credentials flow fit
  better than a social-login-oriented SaaS auth vendor (see `research.md`).
- **Reminders**: a Vercel Cron Job hits `/api/cron/reminders` every 15 minutes (replaces a
  Celery-style worker — the only background job here is a stateless periodic sweep).

## Repository layout

```text
app/         Next.js App Router: pages, Server Actions (app/actions/), REST API (app/api/)
lib/         Drizzle schema/client, Auth.js config, RBAC scoping, i18n, business logic
             (lib/services/*) — the framework-agnostic core both the UI and the API call into
components/  Shared UI (Sidebar, theme/language toggles, week grid, lesson-complete modal)
tests/       Vitest suite against a real Postgres DB (package decrement, permission
             boundaries, payment validation, reminder sweep)
scripts/     scripts/seed.ts — demo data for local validation
design/      Reference design artboards + extracted design tokens
specs/       spec-kit artifacts: spec, plan, research, data model, contracts, task history
```

Two long-lived branches: `web` (this platform) and a future `app` branch (React Native,
same `/api/v1/` surface — out of scope for this MVP, see the constitution).

## Local development

```bash
npm install
vercel link                          # first time only
vercel integration add neon          # provisions Neon Postgres (accept terms in the browser)
vercel env pull .env.local --yes     # pulls DATABASE_URL etc. locally
npm run db:push                      # applies lib/db/schema.ts
npm run seed                         # optional demo data + logins (see quickstart.md)
npm run dev                          # http://localhost:3000
```

Full validation walkthrough: [`specs/001-musicstudio-mvp/quickstart.md`](specs/001-musicstudio-mvp/quickstart.md).

### Tests

```bash
npm run test    # tests/*.test.ts, against a real Postgres DB (local or a Neon branch)
```

## Deploy

```bash
vercel deploy           # preview
vercel deploy --prod    # production
```

Set the `vercel.json` cron job's target (`/api/cron/reminders`) and `CRON_SECRET` env var once
in the Vercel dashboard; Neon's `DATABASE_URL` and `AUTH_SECRET` are provisioned/set the same
way as local dev above.

## Architecture notes

- **Tenant isolation is enforced at the SQL layer**, not just hidden in the UI: every
  service-layer query is scoped by role through `lib/rbac.ts`'s `*Scope()` helpers — a parent
  account cannot retrieve another family's data through any code path. See the constitution,
  Principle I.
- **API-first**: business logic lives in `lib/services/*`, called from both the web UI and
  `/api/v1/*`; nothing is coupled to the web UI's shape.
- Package lesson-count decrement (via a single guarded, idempotent `UPDATE ... WHERE ...`),
  payment validation, and every permission boundary have automated test coverage (Constitution
  Principle III).
