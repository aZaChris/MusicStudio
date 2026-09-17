<!--
Sync Impact Report
Version change: (template) → 1.0.0
Modified principles: n/a (initial ratification)
Added sections: I. Tenant Isolation & RBAC, II. API-First Architecture, III. Test-First on Business Logic,
  IV. MVP Scope Discipline, V. Production-Quality Codebase, VI. Bilingual & Themeable UI;
  Additional Constraints; Development Workflow; Governance
Removed sections: none
Templates requiring updates: ✅ plan-template.md (Constitution Check section — generic, compatible as-is)
  ✅ spec-template.md (generic, compatible as-is)  ✅ tasks-template.md (generic, compatible as-is)
Follow-up TODOs: none
-->

# MusicStudio Constitution

## Core Principles

### I. Tenant Isolation & RBAC (NON-NEGOTIABLE)
A parent account MUST NEVER be able to read, list, or mutate another family's data through
any API endpoint, regardless of what the UI hides. Every DRF viewset/queryset MUST filter by
the requesting user's role and ownership at the ORM query level (not just serializer field
hiding). Role checks (teacher, studio_owner, parent) MUST be enforced via DRF permission
classes, not ad-hoc view logic. Every new endpoint that touches Student, Lesson, Package, or
Payment data MUST ship with a permission-boundary test proving cross-tenant access is denied
(403/404), before it is considered done.
Rationale: this is a multi-tenant system handling other people's children's data and payment
records; a leaked query is not a bug to fix later, it is the one failure mode that ends trust
in the product.

### II. API-First Architecture
The backend is a Django REST Framework API with no server-side rendering of application
views (Django admin excluded). All product features MUST be reachable through the documented
REST API — the React SPA is one client among future clients. Do not couple business logic to
the SPA's shape; a future React Native app MUST be able to consume the same endpoints without
backend changes beyond what any new feature would need anyway.
Rationale: a native mobile app on the same API is explicitly planned next; retrofitting an
API onto a template-coupled backend is far more expensive than building API-first now.

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
Code MUST read as something a team would deploy, not a tutorial: real serializers and
viewsets (no fat views with inline SQL-equivalent logic), migrations committed for every
model change, environment-based settings (no secrets committed, `.env.example` kept current),
and OpenAPI schema generation (drf-spectacular) kept accurate as the API evolves.
Rationale: this project exists in part to demonstrate professional-grade backend work; shortcuts
that wouldn't survive a code review shouldn't survive here either.

### VI. Bilingual & Themeable UI
The frontend MUST support English and Italian (IT is a first-class locale, not an
afterthought — the approved product design is authored in Italian) with a runtime language
toggle, and MUST support light/dark theme via a user-facing toggle. New UI strings MUST go
through the i18n layer, not be hardcoded in components.
Rationale: explicitly required by the product owner; retrofitting i18n and theming after
components are built hardcoded is expensive and error-prone.

## Additional Constraints

- **Stack**: Django + DRF + PostgreSQL + Celery/Redis (backend); React + Vite + TypeScript SPA
  (frontend); JWT auth (djangorestframework-simplejwt); Docker Compose for local dev; AWS
  container deployment (ECS or documented EC2 + Docker Compose) as a deliverable, not an
  afterthought.
- **No payment gateway**: payments are recorded manually (cash/bank transfer/manual entry)
  for MVP — see Principle IV.
- **Secrets**: never committed; all environments configured via env vars, with a checked-in
  `.env.example` documenting required keys.

## Development Workflow

- Features flow through spec-kit: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`. Direct ad-hoc feature work that skips a spec for anything beyond a
  trivial fix is discouraged.
- Every PR/change touching Student, Lesson, Package, or Payment data is self-reviewed against
  Principle I and III before being considered complete.
- Two long-lived branches exist for this product: `web` (this Django/DRF + React platform) and
  a future `app` branch (React Native, same API). Work stays on the branch matching its
  target client.

## Governance

This constitution supersedes ad-hoc practices when they conflict. Amendments are made via
`/speckit-constitution`, require a stated rationale, and bump the version per semantic
versioning (MAJOR: principle removed/redefined incompatibly; MINOR: principle added or
materially expanded; PATCH: clarification/wording). Any change that touches Student, Lesson,
Package, or Payment data must be checked against Principle I and III at review time; violations
must be fixed or explicitly justified in the PR description before merge.

**Version**: 1.0.0 | **Ratified**: 2026-09-17 | **Last Amended**: 2026-09-17
