<!--
Sync Impact Report
Version change: 1.0.0 → 2.0.0
Modified principles: II. API-First Architecture (DRF viewsets → Next.js Route Handlers under
  /api/v1/, same "future mobile client" guarantee); V. Production-Quality Codebase (drf-spectacular/
  Django migrations → typed service layer/Drizzle migrations)
Added sections: none (redefinition, not addition)
Removed sections: none
Modified: Additional Constraints (full stack swap: Django/DRF/Celery/Docker/AWS → Next.js/
  Drizzle/Neon/Auth.js/Vercel Cron/Vercel, all on one platform); Development Workflow (branch
  description updated to Next.js)
Reason for MAJOR bump: the user decided mid-build to deploy backend and frontend together on
  Vercel instead of Django/DRF + Docker/AWS — the concrete stack Principles II and V point at is
  redefined, not just clarified. Principle intent (API-first, production-quality) is unchanged.
Templates requiring updates: ✅ plan-template.md (generic, compatible as-is)
  ✅ spec-template.md (generic, compatible as-is)  ✅ tasks-template.md (generic, compatible as-is)
Follow-up TODOs: none
-->

# MusicStudio Constitution

## Core Principles

### I. Tenant Isolation & RBAC (NON-NEGOTIABLE)
A parent account MUST NEVER be able to read, list, or mutate another family's data through
any code path, regardless of what the UI hides. Every query touching Student, Lesson, Package,
or Payment data MUST be scoped by the requesting user's role and ownership at the SQL level
(via the `lib/rbac.ts` scoping helpers), never by hiding fields in a component after an
unscoped fetch. Role checks (teacher, studio_owner, parent) MUST be enforced in the service
layer, not left to UI conditionals. Every new Route Handler / Server Action that touches this
data MUST ship with a test proving cross-tenant access is denied, before it is considered done.
Rationale: this is a multi-tenant system handling other people's children's data and payment
records; a leaked query is not a bug to fix later, it is the one failure mode that ends trust
in the product.

### II. API-First Architecture
Business logic lives in a framework-agnostic service layer (`lib/services/*`), called from
BOTH the Next.js UI (Server Components for reads, Server Actions for mutations) AND a
documented REST API under `/api/v1/` (Next.js Route Handlers). The web UI is one client among
future clients, not the source of truth for what the backend can do. Do not couple business
logic to the web UI's shape; a future React Native app MUST be able to consume `/api/v1/`
without backend changes beyond what any new feature would need anyway.
Rationale: a native mobile app on the same API is explicitly planned next; retrofitting an API
onto UI-coupled logic is far more expensive than keeping the service layer framework-agnostic
now — this also happens to be idiomatic Next.js (Server Components fetch directly, Route
Handlers exist for external/API consumers), so it costs nothing extra today.

### III. Test-First on Core Business Logic
The following MUST have automated tests before a feature is merged: package lesson-count
decrement on lesson completion, payment status transitions, and every permission boundary
described in Principle I. Tests assert behavior (inputs → outputs/state), not implementation
details. Other CRUD-only surface area may be covered more lightly, but these three areas are
never optional.
Rationale: these are the flows where a silent bug either loses a teacher money (package
count) or leaks another family's data (permissions) — both are unacceptable in a system
people pay teachers through.

### IV. MVP Scope Discipline
Payment gateway integration, native mobile app code, video lessons, file/sheet-music
libraries, recital/event planning, and multi-language support beyond English/Italian are OUT
OF SCOPE until explicitly re-opened by the user. Do not scaffold, stub, or design around
features on this list "for later" — YAGNI applies; the architecture must not block them, but
it must not pay their cost today either.
Rationale: this is a portfolio MVP with a defined success criterion; scope creep is the
primary risk to ever finishing it.

### V. Production-Quality Codebase
Code MUST read as something a team would deploy, not a tutorial: business logic lives in
`lib/services/*`, not inlined in page components or route handlers; Drizzle migrations
committed for every schema change; environment-based config (no secrets committed,
`.env.example` kept current); TypeScript strict mode with no untyped `any` on the data layer.
Rationale: this project exists in part to demonstrate professional-grade work; shortcuts that
wouldn't survive a code review shouldn't survive here either.

### VI. Bilingual & Themeable UI
The frontend MUST support English and Italian (IT is a first-class locale, not an
afterthought — the approved product design is authored in Italian) with a runtime language
toggle, and MUST support light/dark theme via a user-facing toggle. New UI strings MUST go
through the i18n layer, not be hardcoded in components.
Rationale: explicitly required by the product owner; retrofitting i18n and theming after
components are built hardcoded is expensive and error-prone.

## Additional Constraints

- **Stack**: Next.js (App Router, TypeScript) for both frontend and backend, deployed as one
  Vercel project; Drizzle ORM + Neon Postgres (Vercel Marketplace) for persistence; Auth.js
  (Credentials provider, JWT sessions) for authentication — no third-party auth vendor, because
  accounts are invite-only (teachers/admins provision parents) rather than public self-signup,
  so a custom-role credentials flow against our own `users` table is the better fit than a
  social-login-oriented SaaS auth product; Vercel Cron Jobs replace the Celery Beat sweep for
  lesson reminders (the only "background job" in this MVP is a periodic idempotent scan, which
  a scheduled HTTP endpoint handles without needing a queue/worker).
- **No payment gateway**: payments are recorded manually (cash/bank transfer/manual entry)
  for MVP — see Principle IV.
- **Secrets**: never committed; all environments configured via env vars (Vercel-managed in
  prod, `.env.local` locally), with a checked-in `.env.example` documenting required keys.

## Development Workflow

- Features flow through spec-kit: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`. Direct ad-hoc feature work that skips a spec for anything beyond a
  trivial fix is discouraged.
- Every PR/change touching Student, Lesson, Package, or Payment data is self-reviewed against
  Principle I and III before being considered complete.
- Two long-lived branches exist for this product: `web` (this Next.js platform, deployed on
  Vercel) and a future `app` branch (React Native, same `/api/v1/` surface). Work stays on the
  branch matching its target client.

## Governance

This constitution supersedes ad-hoc practices when they conflict. Amendments are made via
`/speckit-constitution`, require a stated rationale, and bump the version per semantic
versioning (MAJOR: principle removed/redefined incompatibly; MINOR: principle added or
materially expanded; PATCH: clarification/wording). Any change that touches Student, Lesson,
Package, or Payment data must be checked against Principle I and III at review time; violations
must be fixed or explicitly justified in the PR description before merge.

**Version**: 2.0.0 | **Ratified**: 2026-09-17 | **Last Amended**: 2026-09-17
