<div align="center">

<img src="frontend/public/favicon.svg" width="88" alt="MusicStudio logo">

# MusicStudio

**Lessons, prepaid packages and payments for private music teachers and small studios.**<br>
A production-grade Django REST API, a React web portal and an Expo mobile app, built spec-first.

[![CI](https://github.com/aZaChris/MusicStudio/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aZaChris/MusicStudio/actions/workflows/ci.yml)
![Coverage](https://img.shields.io/badge/coverage-96.45%25-2ea44f)
![Python](https://img.shields.io/badge/python-3.12-3776ab?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/django-5.2_LTS-0c4b33?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-16_%7C_18-4169e1?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/react-19-149eca?logo=react&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-ef852e)](LICENSE)

[Features](#features) · [Screenshots](#screenshots) · [Architecture](#architecture) ·
[Engineering highlights](#engineering-highlights) · [Measured](#measured) · [Limits](#limits-on-purpose) ·
[Quick start](#quick-start) · [Docs](#documentation) · [Case study](docs/case-study.md)

</div>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/screenshots/home-dark.png">
  <img src="docs/assets/screenshots/home-light.png" alt="The teacher's home: active students, pending payments, packages running low, upcoming lessons and recent payments">
</picture>

## Status

**In production since 2026-11-14**, on a self-hosted [Coolify](https://coolify.io) server, with a
staging copy: the staging portal is at <https://stagingwebmusic.christianseminerio.dev/> and its
API at `https://stagingapimusic.christianseminerio.dev/api/v1`. Stripe is in test mode, online
payments to the studio's own account are built but switched off, and the privacy texts in
`docs/privacy/` are drafts waiting for a legal review.

## Why it exists

A music teacher with twenty students runs the business on paper or in a spreadsheet: who has
lessons left in their package, who paid, who skipped last week. MusicStudio replaces that with
one register: the teacher schedules lessons, each completed lesson consumes one "beat" of a
prepaid package, payments are recorded or paid online, and parents follow their child's lessons
from a read-only portal.

It is also a deliberate training ground: every phase ships with its tests, an ADR for each
non-obvious decision and study notes (in Italian) that explain the concept behind it.

## Features

- **Studios as tenants**: a solo teacher or a studio with an owner and several teachers;
  invitations with role, consent and expiry.
- **Lessons**: recurring weekly slots, completion with notes, cancellation, no-shows, and a
  database guarantee that no teacher or student is ever double-booked.
- **Packages**: prepaid bundles shown as a row of beats; one lesson consumes one beat, exactly
  once, even under concurrent requests. "Running low" alerts below three.
- **Payments**: cash and bank transfers recorded by the teacher, or Stripe Checkout
  (test mode) fulfilled only by verified, idempotent webhooks, with hourly reconciliation.
- **Cash register and receipts**: a recorded payment is final and is corrected with a reversal
  row, never edited; period totals, CSV/PDF export, payment instructions for parents and
  numbered non-fiscal receipts.
- **Online payments to the studio's own Stripe account** (Stripe Connect, direct charges, no
  platform fee), with refunds and disputes as reversal rows. Built and tested, switched off.
- **Parent portal**: next lesson, attendance and payments, read-only.
- **Accounts and security**: sign-up with email confirmation, password reset, lockout, TOTP
  two-factor with recovery codes, rotating refresh tokens with revocation.
- **Privacy**: GDPR export and erasure (as anonymisation that keeps accounting records),
  retention jobs, an audit log, and lesson notes encrypted at rest. An inventory test makes sure
  every model is either exported or excluded with a written reason.
- **Operator-only admin**: staff accounts without a studio role, TOTP in production, the API's
  lockout, read-only financial records, every change audited.
- **API versioning policy**: 90 days' notice, standard `Deprecation`/`Sunset` headers, `410` after
  removal, and a CI job that blocks unregistered breaking changes to the contract.

## Screenshots

| Student and package | Parent portal |
|---|---|
| <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/screenshots/student-dark.png"><img src="docs/assets/screenshots/student-light.png" alt="A student's page with the package as a row of beats"></picture> | <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/screenshots/parent-dark.png"><img src="docs/assets/screenshots/parent-light.png" alt="The parent portal with the next lesson and remaining beats"></picture> |
| **Landing** | **On a phone** |
| <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/screenshots/landing-dark.png"><img src="docs/assets/screenshots/landing-light.png" alt="The public landing page"></picture> | <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/screenshots/home-mobile-dark.png"><img src="docs/assets/screenshots/home-mobile-light.png" alt="The portal at phone width" width="260"></picture> |

Light or dark follows your GitHub theme. The screenshots are of the production build against the real
API with sample data, taken once; the script that made them was removed together with the demo data
(see the git history).

## Architecture

```mermaid
flowchart LR
  subgraph Clients
    SPA["React SPA<br/>(frontend/)"]
    APP["Expo app<br/>(branch mobile)"]
  end
  subgraph API["Django REST API — modular monolith"]
    direction TB
    V["views + serializers<br/>(thin)"] --> S["services.py (writes)<br/>selectors.py (reads)"]
    S --> SC["common/scoping.py<br/>tenant isolation"]
  end
  SPA -- "JWT, OpenAPI types" --> V
  APP -- "JWT, OpenAPI types" --> V
  SC --> PG[("PostgreSQL 16<br/>exclusion constraints")]
  S -- "outbox, tasks" --> R[("Redis")] --> W["Celery worker + beat<br/>reminders, webhooks,<br/>reconciliation, retention"]
  W --> PG
  STRIPE["Stripe (test mode)"] -- "signed webhooks" --> V
  W -- "Checkout, reconcile" --> STRIPE
```

One Django app per domain (`accounts`, `studios`, `students`, `lessons`, `packages`,
`payments`, `notifications`, `privacy`, `audit`, plus `common`). Writes live in `services.py`,
reads in `selectors.py`; views and serializers stay thin. The OpenAPI contract
(`backend/openapi.yaml`) is committed and checked in CI, and both clients generate their types
from it.

## Engineering highlights

Each line links to the decision record or study note that explains it.

- **Tenant isolation for reads and writes**, enforced in one place at the ORM level and proven
  by a cross-tenant IDOR test suite. → [multi-tenancy](docs/learning/concetti/multi-tenancy.md),
  [BOLA](docs/learning/concetti/isolamento-tenant-e-bola.md)
- **No double booking, even under concurrency**: PostgreSQL exclusion constraints, with a
  retry-then-409 guard for the deadlocks they can cause.
  → [exclusion constraints](docs/learning/concetti/exclusion-constraint.md)
- **Payments that cannot be fulfilled twice**: signature-checked Stripe webhooks from an IP
  allowlist, processed idempotently, plus hourly reconciliation.
  → [idempotent webhooks](docs/learning/concetti/webhook-idempotenti.md),
  [real client IP](docs/learning/concetti/ip-reale-dietro-proxy.md)
- **Reliable background work**: an outbox for reminders, idempotent Celery tasks, and an API
  that stays up when Redis is down (throttles fail open).
  → [idempotent tasks](docs/learning/concetti/task-celery-idempotenti.md)
- **Performance with evidence**: query-count budgets on the main endpoints, and a Locust
  baseline at 50 users over 78,000 lessons with 0 errors on a laptop (numbers below).
  → [N+1](docs/learning/concetti/orm-e-problema-n-piu-1.md),
  [load test](docs/loadtest/2026-11-09/README.md)
- **Security reviewed every phase** against the OWASP API Security Top 10, with a verdict and a
  proof for each risk. → [OWASP walk](docs/learning/concetti/sicurezza-api-owasp.md)
- **Safe API evolution**: `oasdiff` compares every pull request's contract with `main`. Its
  default rules raised 13 false alarms on our own history, so it was tuned on that real run; a
  renamed field still fails with 10 errors.
  → [ADR-040](docs/learning/adr/ADR-040-versionamento-e-deprecazione-api.md),
  [policy](docs/operations/api-versioning-policy.md)
- **An admin that cannot be abused**: the one place that bypasses tenant isolation is gated to
  operators with TOTP, and a test enumerating it found a library exposing refresh tokens there.
  → [ADR-041](docs/learning/adr/ADR-041-admin-solo-operatori-con-totp.md)
- **A GDPR export that cannot silently fall behind**: a model nobody classified fails CI.
  → [ADR-042](docs/learning/adr/ADR-042-inventario-dell-export-gdpr.md)
- **Operable in production**: JSON logs with request IDs, Sentry, liveness and readiness
  probes, off-site backups with a restore drill, Docker Compose on Coolify.
  → [runbook](docs/operations/runbook.md)

## Measured

Numbers come from commands, with their date. They are re-run, not edited.

- **Backend tests** (2026-11-25, `cd backend && uv run pytest`, PostgreSQL 16, laptop):
  1,242 passed, line and branch coverage 96.45% (CI floor: 90%).
- **Load test** (2026-11-09, Locust, 50 users, 78,000 lessons, client and server on the same
  laptop, two runs): 0 errors in both. Read endpoints p95 62-110 ms with a fast ramp and
  400-560 ms with a slow one. Sign-in is the slow path on purpose (password hashing is
  deliberately expensive): p95 12 s when 50 users sign in at once.
  → [report](docs/loadtest/2026-11-09/README.md)
- **GDPR export** of the largest realistic family (2026-11-25: 1 parent, 3 children, 2 years of
  weekly lessons, 312 lessons, 78 payments): 47-167 ms, so it stays synchronous.

## Limits, on purpose

- **No real money**: Stripe is in test mode; online payments are switched off until a
  constitution amendment and the owner's decision.
- **No `v2`**: the versioning mechanism exists; a `v2` is created only for the first real
  breaking change.
- **No AWS, no Kubernetes**: one server with Docker Compose is enough at this scale.
- **Tenant isolation lives in the application**, enforced in one module and tested; PostgreSQL
  row-level security is a possible next layer, not done.
- **The web portal keeps its refresh token in `localStorage`** (ADR-023): an accepted, documented
  risk; an httpOnly cookie is the next step.
- **Load numbers come from a laptop**: they find problems, they do not promise capacity.
- **Legal texts are drafts** until a professional reviews them.

## Tech stack

| Layer | Choice |
|---|---|
| API | Python 3.12, Django 5.2 LTS, Django REST Framework, simplejwt, drf-spectacular |
| Data and jobs | PostgreSQL 16 (CI also on 18), Redis, Celery worker and beat |
| Payments | Stripe Checkout, test mode only |
| Web | React 19, TypeScript, Vite, TanStack Query, Vitest, design tokens in `design/system/` |
| Mobile | Expo (React Native), on branch [`mobile`](https://github.com/aZaChris/MusicStudio/tree/mobile) |
| Quality | pytest + factory_boy on real PostgreSQL, 90% coverage floor, ruff, mypy, pre-commit, gitleaks |
| Deploy | Docker Compose on self-hosted [Coolify](https://coolify.io), Sentry; no AWS |

## Quick start

With Docker:

```bash
cp .env.example .env
docker compose up --build                                  # API on http://localhost:8000
docker compose --profile frontend up                       # web portal on http://localhost:5173
```

Without Docker (PostgreSQL reachable through `DATABASE_URL`):

```bash
cd backend && uv sync
cp ../.env.example .env                                    # then point DATABASE_URL at your PostgreSQL
uv run python manage.py migrate
uv run python manage.py runserver
cd ../frontend && npm ci && npm run dev
```

There are no demo accounts and no default credentials: register from the portal, or create the first
account from the backend terminal (the command asks for the password and never takes it on the command
line): `python manage.py create_teacher --email you@example.com --studio-name "Your studio"`.
API docs at `http://localhost:8000/api/docs/`.

### Quality gate (the same as CI)

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run python manage.py makemigrations --check --dry-run
uv run pytest                     # needs PostgreSQL; fails under 90% coverage
cd ../frontend && npm run lint && npm test && npm run build
```

### Deploy

`docker-compose.coolify.yml` is the production stack (health checks, memory limits, backups, no
published ports). Deploy steps, backups and incident procedures are in the runbook,
[`docs/operations/runbook.md`](docs/operations/runbook.md).

## Documentation

The study documentation is a deliverable, written in Italian:

- [`docs/learning/00-indice.md`](docs/learning/00-indice.md): reading order and phase summaries.
- [`docs/case-study.md`](docs/case-study.md) (English): three real bugs, their root cause and the fix.
- [`docs/operations/api-versioning-policy.md`](docs/operations/api-versioning-policy.md) (English):
  what the API promises to client developers.
- [`docs/learning/adr/`](docs/learning/adr/): 42 architecture decision records.
- [`docs/learning/concetti/`](docs/learning/concetti/): 37 concept notes, from N+1 queries to TOTP.
- [`docs/knowledge-base/`](docs/knowledge-base/README.md): non-trivial problems, their root
  cause and how it was confirmed.
- [`specs/`](specs/): spec-kit artifacts (spec, plan, tasks) for every feature;
  principles in [`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Roadmap

- [x] Production foundations: settings, CI, health checks, Docker
- [x] Domain integrity: exclusion constraints, concurrency-safe packages
- [x] Celery and Stripe payments (test mode)
- [x] Production readiness: Sentry, JSON logs, load test, off-site backups, OWASP, token revocation
- [x] Web portal hardening: rotating-token session, generated types, every page, tests
- [x] Security, privacy and accounts: sign-up, invitations, MFA, GDPR, audit log, encryption
- [x] Cash register, payment instructions and non-fiscal receipts
- [x] Online payments to the studio's own Stripe account (built, switched off)
- [x] Polish: API versioning and deprecation, admin hardening, complete GDPR export, write-up

Releases follow the phases: see [Releases](https://github.com/aZaChris/MusicStudio/releases).

## Repository layout

```text
backend/            Django project (uv): config/, apps/<domain>/, Dockerfile, openapi.yaml
frontend/           React SPA (Vite): pages, generated API types, Vitest tests
design/system/      design tokens and CSS kit shared with the mobile app
docs/               study docs, knowledge base, operations, load tests, privacy
specs/              spec-kit artifacts per feature
scripts/            study-docs export, README screenshots
```

Branches: `main` is the production line for the API and the web portal; `mobile` holds the
Expo app. Earlier rewrites are kept as `archive/*` tags.

## License

[MIT](LICENSE) © 2026 Christian Seminerio
