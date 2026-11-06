> **Historical note (2026-11-06):** this document describes feature 001 as built. The AWS deployment target was replaced by Coolify (self-hosted) in feature 002 — see `specs/002-production-foundations/` and `docs/learning/adr/ADR-003-coolify-al-posto-di-aws.md`. AWS references below are kept only as history.

# Implementation Plan: MusicStudio MVP — Teacher & Parent Platform

**Branch**: `web` (feature tracked as `001-musicstudio-mvp`) | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-musicstudio-mvp/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A Django REST Framework API (PostgreSQL, JWT auth, Celery/Redis for background reminders)
backing a React + Vite + TypeScript SPA with role-scoped UI (teacher/studio_owner vs. parent),
bilingual (EN/IT) with a light/dark theme toggle. Core loop: teacher runs their week, marks
lessons complete (which atomically decrements a package's remaining-lesson count), tracks
manual payments; parents get a strictly-scoped read-only portal; Celery Beat drives 24h-before
lesson reminders and low-package warnings. Ships with Docker Compose for local dev and a
documented AWS container deployment, matching the design reference in `design/reference/`.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x / Node 22 (frontend build tooling)

**Primary Dependencies**: Django 5.x, djangorestframework, djangorestframework-simplejwt,
drf-spectacular, django-cors-headers, django-filter, celery, redis (broker/result backend),
psycopg (PostgreSQL driver); React 18, Vite, react-router, react-i18next, TanStack Query
(server-state/cache for the SPA), a lightweight component/styling layer matching the design
tokens in `design/tokens.md` (plain CSS custom properties + CSS modules — no heavyweight UI kit
needed for this surface area).

**Storage**: PostgreSQL 16 (all persistent data — users, students, lessons, packages,
payments). Redis 7 as Celery broker/result backend only (no app data cached there for MVP).

**Testing**: pytest + pytest-django + factory_boy (backend: model/business-logic/permission
tests); Vitest + React Testing Library (frontend: component/flow tests, kept light for MVP).

**Target Platform**: Linux containers (Docker Compose locally; AWS ECS Fargate, or a
documented EC2 + Docker Compose fallback, in production). Browser-only frontend (no SSR).

**Project Type**: Web application (separate `backend/` API and `frontend/` SPA, per Option 2
below) — chosen because the constitution requires an API-first backend that a future React
Native app can consume unchanged (Principle II).

**Performance Goals**: Not a high-throughput system (single studio, ≤10 teachers, low hundreds
of students) — no special performance engineering beyond sane DB indexes on
teacher/student/date lookups and pagination on list endpoints.

**Constraints**: Parent-scoped queries MUST be enforced at the ORM/queryset level, never only
in the serializer (Constitution Principle I). No secrets committed; all config via environment
variables with a checked-in `.env.example`.

**Scale/Scope**: MVP: 1 studio-scale deployment per install (not multi-studio SaaS in this
phase), ≤10 teachers, ≤~300 students, ~6 REST resource groups (auth, studios/teachers,
students/parents, packages, lessons, payments), ~15-20 screens/views across teacher and parent
UI combined.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Tenant Isolation & RBAC | DRF permission classes + queryset-level filtering per role; permission-boundary tests required for every Student/Lesson/Package/Payment endpoint | PASS (enforced in data-model/contracts design below) |
| II. API-First Architecture | Django is API-only (DRF), SPA is a pure REST client; no view logic depends on the React SPA's shape | PASS |
| III. Test-First on Core Business Logic | Package decrement, payment status transitions, and permission boundaries are explicitly scoped as required test areas in tasks.md | PASS (enforced at task-planning stage, §Phase 2) |
| IV. MVP Scope Discipline | No payment gateway, mobile app, video, file library, recital planning, or extra languages in this plan | PASS |
| V. Production-Quality Codebase | Real serializers/viewsets per app, migrations per model, env-based settings, drf-spectacular schema | PASS |
| VI. Bilingual & Themeable UI | react-i18next with en/it resource bundles from day one; CSS custom properties driving a `data-theme` attribute for light/dark | PASS |

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
backend/
├── config/                    # Django project: settings/{base,dev,prod}.py, urls.py, celery.py
├── apps/
│   ├── accounts/               # User model (role: teacher/studio_owner/parent), JWT views
│   ├── studios/                # Studio, Teacher
│   ├── students/                # Student, ParentAccount, parent<->student link
│   ├── packages/                # Package + decrement business logic
│   ├── lessons/                 # Lesson, completion flow (decrements Package)
│   ├── payments/                # Payment
│   └── notifications/           # Celery tasks: 24h reminder, low-package warning
├── manage.py
├── pyproject.toml               # deps + pytest config
└── tests/                       # cross-app integration/permission tests (per-app unit tests live in apps/*/tests/)

frontend/
├── src/
│   ├── api/                     # typed REST client (per resource)
│   ├── auth/                    # JWT storage/refresh, role-based route guards
│   ├── features/
│   │   ├── teacher/              # dashboard, roster, student detail, payments
│   │   └── parent/                # parent portal views
│   ├── components/               # shared UI primitives (cards, calendar grid, nav)
│   ├── theme/                     # CSS custom properties, light/dark tokens (design/tokens.md)
│   ├── i18n/                      # en.json, it.json, react-i18next setup
│   └── routes/
├── index.html
├── vite.config.ts
└── package.json

infra/
├── docker-compose.yml            # django, postgres, redis, celery worker, celery beat, frontend dev server
├── backend.Dockerfile
├── frontend.Dockerfile
└── aws/                          # ECS task defs (or EC2 + Docker Compose doc) — deployment deliverable

design/                           # already present: reference .dc.html artboards + tokens.md
```

**Structure Decision**: Option 2 (separate `backend/` API + `frontend/` SPA), per Constitution
Principle II — the API must stand on its own for a future React Native client. `infra/` holds
the Docker Compose/AWS deployment deliverable called out explicitly in the brief.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
