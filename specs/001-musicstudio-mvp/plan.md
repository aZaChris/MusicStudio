# Implementation Plan: MusicStudio MVP — Teacher & Parent Platform

**Branch**: `web` (feature tracked as `001-musicstudio-mvp`) | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-musicstudio-mvp/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

**Amended 2026-09-17**: originally planned as Django/DRF + React/Vite + Docker/AWS (see git
history for that version, superseded); the user decided mid-build to run backend and frontend
together on Vercel. Rebuilt as a single Next.js (App Router, TypeScript) app: a `lib/services/*`
business-logic layer (Drizzle + Neon Postgres) called from both Server Components/Server
Actions (the web UI) and `/api/v1/*` Route Handlers (the documented REST surface for a future
mobile client). Role-scoped UI (teacher/studio_owner vs. parent), bilingual (EN/IT) with a
light/dark theme toggle. Core loop: teacher runs their week, marks lessons complete (which
atomically decrements a package's remaining-lesson count via a guarded conditional UPDATE),
tracks manual payments; parents get a strictly-scoped read-only portal; a Vercel Cron Job hits
a sweep endpoint every 15 min for 24h-before lesson reminders. Matches the design reference in
`design/reference/`.

## Technical Context

**Language/Version**: TypeScript 5.x, Node.js 22, Next.js 16 (App Router, Turbopack)

**Primary Dependencies**: `next`, `react` 19; `drizzle-orm` + `pg` (node-postgres — same driver
against local Postgres for tests and Neon's pooled connection string in prod, since this app
runs on the Node.js runtime rather than Edge); `next-auth` (Auth.js v5, Credentials provider,
JWT sessions); `bcryptjs` (password hashing); `drizzle-kit` (migrations); `vitest` (tests). No
i18n/theming library — a small `lib/i18n.ts` dictionary + CSS custom properties from
`design/tokens.md` cover the whole surface area (see research.md for why).

**Storage**: Neon Postgres (serverless, provisioned via the Vercel Marketplace) — all
persistent data. No separate cache/broker: the only "background job" (reminder sweep) is a
stateless periodic HTTP call, not a job queue.

**Testing**: Vitest against a real Postgres database (local Postgres or a Neon branch) for the
service layer — package decrement, permission scoping, payment validation, reminder sweep
(Constitution Principle III). No mocked DB layer.

**Target Platform**: Vercel (Node.js runtime / Fluid Compute). No containers, no separate
infra to operate — this replaces the previous Docker Compose/AWS deliverable.

**Project Type**: Single Next.js project at the repo root (frontend UI + `/api/v1/*` backend
in one codebase/deployment) — chosen because Vercel's idiomatic pattern for "frontend and
backend together" is one Next.js app, not separate services (see research.md).

**Performance Goals**: Not a high-throughput system (single studio, ≤10 teachers, low hundreds
of students) — no special performance engineering beyond sane DB indexes and pagination-free
list endpoints at this scale.

**Constraints**: Parent-scoped queries MUST be enforced at the SQL level via `lib/rbac.ts`,
never only in a component (Constitution Principle I). No secrets committed; all config via
environment variables (Vercel-managed in prod, `.env.local` locally) with a checked-in
`.env.example`.

**Scale/Scope**: MVP: 1 studio-scale deployment per install (not multi-studio SaaS in this
phase), ≤10 teachers, ≤~300 students, ~6 API resource groups (auth, studios/teachers,
students/parents, packages, lessons, payments), ~10 pages across teacher and parent UI combined.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Tenant Isolation & RBAC | `lib/rbac.ts` scoping helpers used by every service-layer query; permission tests required for Student/Lesson/Package/Payment | PASS |
| II. API-First Architecture | `lib/services/*` is framework-agnostic; both the web UI and `/api/v1/*` Route Handlers call it — no logic lives only in a page component | PASS |
| III. Test-First on Core Business Logic | Package decrement, payment validation, and permission boundaries are explicitly scoped as required test areas in tasks.md | PASS |
| IV. MVP Scope Discipline | No payment gateway, mobile app, video, file library, recital planning, or extra languages in this plan | PASS |
| V. Production-Quality Codebase | Service layer separated from route/page code, Drizzle migrations per schema change, env-based config | PASS |
| VI. Bilingual & Themeable UI | `lib/i18n.ts` dictionaries from day one; CSS custom properties driving a `data-theme` attribute for light/dark | PASS |

No violations — Complexity Tracking table below stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-musicstudio-mvp/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── layout.tsx, page.tsx, globals.css   # root layout (theme/i18n cookies), "/" role redirect
├── login/                               # LoginForm (client) + signInAction
├── dashboard/                           # teacher/studio_owner dashboard (Server Component)
├── students/, students/[id]/            # roster, student detail
├── payments/                            # payments list + register form
├── parent/                              # parent portal (searchParams-driven student switch)
├── actions/                             # Server Actions: lessons.ts, payments.ts, auth.ts
└── api/
    ├── auth/[...nextauth]/               # Auth.js handler
    ├── v1/                               # REST surface: students, lessons, packages, payments, dashboard
    └── cron/reminders/                   # Vercel Cron target (Bearer CRON_SECRET)

lib/
├── db/schema.ts, db/index.ts            # Drizzle schema + lazy db client
├── auth.ts                              # Auth.js config (Credentials, JWT sessions)
├── rbac.ts                              # Constitution Principle I choke point (scoping helpers)
├── i18n.ts, get-locale.ts               # dictionaries (client-safe) / cookie read (server-only)
└── services/                            # lessons, students, packages, payments, dashboard,
                                          # reminders, email — framework-agnostic business logic

components/                              # Sidebar, ThemeToggle, LanguageToggle, WeekGrid,
                                          # LessonCompleteModal
types/next-auth.d.ts                     # Session/User/JWT module augmentation
proxy.ts                                 # route protection (Next.js 16 middleware rename)
vercel.json                              # cron schedule
drizzle.config.ts
tests/                                   # Vitest: lessons, permissions, payments, reminders
scripts/seed.ts                          # demo data (see quickstart.md)

design/                                  # already present: reference .dc.html artboards + tokens.md
```

**Structure Decision**: single Next.js project at the repo root — Vercel's idiomatic "frontend
+ backend together" shape (see research.md "Local dev & deployment"). `lib/services/*` is the
framework-agnostic core Constitution Principle II requires; both the UI and `/api/v1/*` call
into it, so a future React Native app only needs the latter.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
