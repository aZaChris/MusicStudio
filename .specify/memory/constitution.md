<!--
Sync Impact Report
Version change: 3.1.0 → 3.1.1 (PATCH: `staging/backend` renamed `main` (production, protected) and
  `staging/mobile` renamed `mobile`; `refactor/*` archived as tags; no principle changed)

Previous report (3.1.0):
Version change: 3.0.1 → 3.1.0 (MINOR: Principle X added — privacy by design for minors' data)
Modified principles: none
Added principles: X. Privacy by Design for Minors' Data
Added sections: none
Removed sections: none
Templates requiring updates:
  ✅ .specify/templates/plan-template.md (gate X added)
  ✅ .specify/templates/spec-template.md (generic, compatible as-is)
  ✅ .specify/templates/tasks-template.md (generic, compatible as-is)
Follow-up TODOs: privacy drafts in docs/privacy/ must be validated by a professional (owner).

Previous report (3.0.1):
Version change: 3.0.0 → 3.0.1 (PATCH: branches `web`/`app` archived as tags; work moved to
  `staging/backend` and `staging/mobile`; no principle changed)

Previous report (3.0.0):
Version change: 2.0.0 → 3.0.0 (MAJOR: Principle VI redefined — the web client in frontend/ is
  re-opened and developed on this branch)
Modified principles:
  VI. Clients Are Out of Scope; Backend Stays Bilingual → VI. The Web Client Is In Scope; Other
    Clients Stay Isolated
  VII. Automated Quality Gate (+ frontend CI job)
  VIII. Decisions & Study Docs Ship With Code (covers the web client)
  IX. Security Verified Per Phase (OWASP walk covers the SPA: XSS, token storage)
Added sections: Additional Constraints → web client stack
Removed sections: none
Templates requiring updates:
  ✅ .specify/templates/plan-template.md (gate VI reworded)
  ✅ .specify/templates/spec-template.md (generic, compatible as-is)
  ✅ .specify/templates/tasks-template.md (generic, compatible as-is)
  ✅ CLAUDE.md (frontend no longer "never modify"; roadmap row for the web track)
Follow-up TODOs: none

Previous report (2.0.0):
Sync Impact Report
Version change: 1.0.0 → 2.0.0 (MAJOR: Principle VI redefined, Principle IV scope changed,
  deployment target changed from AWS to Coolify)
Modified principles:
  I. Tenant Isolation & RBAC → extended to write paths (related-field querysets)
  III. Test-First on Core Business Logic → III. Tested Features & Query Budgets (every feature
    ships tests; query-count assertions on main endpoints)
  IV. MVP Scope Discipline → IV. Phased Scope Discipline (payment gateway re-opened for phase 3,
    Stripe test mode only)
  V. Production-Quality Codebase → V. Modular Monolith with an Explicit Service Layer
  VI. Bilingual & Themeable UI → VI. Clients Are Out of Scope; Backend Stays Bilingual
Added principles: VII. Automated Quality Gate (CI), VIII. Decisions & Study Docs Ship With Code,
  IX. Security Verified Per Phase (OWASP API Top 10)
Added sections: Deployment & Operations constraints
Removed sections: AWS deployment constraint
Templates requiring updates:
  ✅ .specify/templates/plan-template.md (Constitution Check gates listed)
  ✅ .specify/templates/tasks-template.md (tests no longer optional; docs/ADR tasks)
  ✅ .specify/templates/spec-template.md (generic, compatible as-is)
  ✅ README.md (stack/deploy section rewritten in feature 002)
Follow-up TODOs: GitHub branch protection must be enabled by the repo owner (cannot be set from
  code) for Principle VII's "blocks merge" to be enforced.
-->

# MusicStudio Constitution

## Core Principles

### I. Tenant Isolation & RBAC (NON-NEGOTIABLE)
A user MUST NEVER read, list, create, or mutate data belonging to another tenant (another
teacher, studio, or family) through any API endpoint. Isolation is enforced at the ORM query
level on BOTH paths:
- **Reads**: every queryset touching Student, Lesson, Package, or Payment is filtered by the
  requesting user's role and ownership.
- **Writes**: every related field a client can set (e.g. `student`, `package`) MUST validate
  against a queryset scoped to the requesting user, so a foreign id is rejected.
Role checks (teacher, studio_owner, parent) MUST be DRF permission classes, not ad-hoc view
logic. Out-of-tenant objects return 404, not 403. Every endpoint that touches tenant data MUST
ship with a test proving cross-tenant reads AND writes are denied.
Rationale: this system holds other people's children's data and payment records; a leaked
query ends trust in the product. Feature 001 scoped reads but not writes — the gap is closed
here and must not reopen.

### II. API-First Architecture
The backend is a Django REST Framework API with no server-rendered application views (Django
admin excluded). Every product feature MUST be reachable through the versioned, documented
REST API (`/api/v1/`, OpenAPI via drf-spectacular kept accurate). Business logic MUST NOT be
coupled to any client's shape: the web SPA and the mobile app are clients among others.
Rationale: several clients (web, Expo app) consume the same API; retrofitting is costly.

### III. Tested Features & Query Budgets
Every feature MUST ship with automated tests in the same change (pytest + factory_boy, against
real PostgreSQL). Tests assert behaviour, not implementation. Mandatory coverage:
- business-critical paths (package decrement, payment rules, scheduling rules);
- every permission boundary from Principle I;
- every main list and detail endpoint MUST assert its query count
  (`django_assert_num_queries` / `assertNumQueries`) so N+1 regressions fail the build.
Line coverage of `backend/apps` MUST stay at or above the threshold configured in CI (90%).
Rationale: silent bugs here lose teachers money or leak data; query counts are the cheapest
guard against the most common ORM performance bug.

### IV. Phased Scope Discipline
Work follows the phase roadmap in the active plan (1 foundations, 2 domain, 3 Celery &
payments, 4 production, 5 polish); a phase starts only when the previous one is complete.
Payment gateway integration is allowed from phase 3 in **Stripe test mode only**. Native app
code, video lessons, sheet-music libraries, and event planning remain OUT OF SCOPE until the
user re-opens them. YAGNI: the architecture must not block future features, but must not pay
their cost today.
Rationale: a portfolio project dies of scope creep; phases keep it shippable at every step.

### V. Modular Monolith with an Explicit Service Layer
One deployable Django project; one Django app per business domain (`accounts`, `studios`,
`students`, `packages`, `lessons`, `payments`, `notifications`, plus `common` for
cross-cutting code). Inside each app:
- `services.py` holds write use-cases (transactions, invariants, side effects);
- `selectors.py` holds non-trivial reads (scoping, prefetching, annotations);
- views and serializers stay thin: HTTP/validation in, call a service/selector, data out;
- models hold data, constraints, and trivial derived properties only.
Apps import each other only through services/selectors or models, never through views.
Migrations are committed for every model change; static types are checked with mypy.
Rationale: business rules in one obvious place are testable without HTTP and reviewable at
an interview; a monolith keeps operations simple for a 1–10 teacher product.

### VI. The Web Client Is In Scope; Other Clients Stay Isolated
The React SPA in `frontend/` is developed on this branch as a client of this API, with the
same discipline as the backend where it applies:
- response types MUST be generated from `backend/openapi.yaml`; no hand-written response types;
- session handling MUST match the backend: store the rotated refresh token after every
  refresh, one refresh in flight at a time, logout through `POST /api/v1/auth/logout/`, every
  cached response cleared on logout;
- the server is the authority on permissions: the SPA handles 401/403/404 explicitly and never
  infers access from a cached role;
- every feature ships tests (Vitest + Testing Library, network mocked at the `fetch` boundary);
- user-facing text is bilingual EN/IT through i18next.
The earlier rewrites `web` (Next.js) and `app` (Expo) are archived as tags `archive/web` and
`archive/app`, which MUST NOT be moved. The mobile app lives on branch `mobile` under its
own constitution. The backend keeps EN/IT where it owns
user-facing text (emails, admin, error messages via Django i18n).
Rationale: the owner re-opened the web portal; a client that drifts from the contract or
mishandles rotating tokens breaks against this backend (it did: phase 4 rotation logged SPA
users out after ~30 minutes).

### VII. Automated Quality Gate
A GitHub Actions workflow MUST run on every push and pull request: ruff (lint + format
check), mypy (django-stubs, djangorestframework-stubs), a migrations-in-sync check, and
pytest with coverage against PostgreSQL and Redis service containers. A red pipeline blocks
merge (enforced via branch protection on the default branch). The same checks run locally
through pre-commit. A separate job checks the SPA in `frontend/`: typecheck, lint, tests,
production build, and that the generated API types match `backend/openapi.yaml`.
Rationale: standards that are not enforced by a machine erode.

### VIII. Decisions & Study Docs Ship With Code
Every non-trivial architectural decision MUST produce an ADR in `docs/learning/adr/`
(context, decision, rejected alternatives, consequences). Every feature MUST produce, in the
same PR, Italian study documentation in `docs/learning/` (concept files, glossary entries,
interview Q&A) following the format defined in `docs/learning/00-indice.md`, and update that
index. Code, comments, identifiers, and commit messages are in English; study docs in Italian.
Commit bodies explain *why*. The web client is documented in the same `docs/learning/` tree.
Rationale: the project trains its developer; undocumented decisions cannot be defended.

### IX. Security Verified Per Phase
At the end of every phase the OWASP API Security Top 10 checklist MUST be walked against the
API and the result recorded in `docs/learning/` (what is covered, what is open). No secrets
in the repository; authentication endpoints are rate-limited; production settings fail fast
when required configuration is missing. From the web client's re-opening, the walk also
covers the SPA (XSS exposure, token storage, what the browser bundle contains).
Rationale: security reviewed once at the end is security never reviewed.

### X. Privacy by Design for Minors' Data
The product holds data about children and families; privacy is a default, not an option.
- **Minimisation**: collect only what a feature uses. No date of birth (an "adult" flag is
  enough), no phone, no address, no card data — card data never reaches the backend.
- **Minors only through a parent**: a minor never has an account; their parent signs in for
  them, and the parent's consent (who, when, notice version) is recorded before the parent sees
  the child's data.
- **Rights built in**: a family can export all its data and request erasure from the product.
  Erasure anonymises in place what the law requires the studio to keep (payment amounts and
  dates) and removes the rest; retention periods are enforced by a scheduled job.
- **Encryption of free text about students**: notes and similar free text are encrypted at the
  application level with a key from the environment that can be rotated.
- **Audit**: sensitive actions (authentication, credentials, invitations, roles, consent,
  export, erasure, payments) are recorded append-only with actor, target, time and request id.
- **No personal data in logs or error reports**: identifiers only; a test proves it on the
  authentication flows.
- **Secrets**: never in the repository or its history; CI scans the full history and blocks
  on a finding.
- **No account enumeration**: anonymous account endpoints answer the same whether or not an
  address is registered.
Rationale: a leak of children's data or an unanswerable GDPR request ends the product; these
rules are cheap when built in and very expensive to retrofit.

## Additional Constraints

- **Stack**: Python 3.12, Django (current LTS), Django REST Framework (API-only), PostgreSQL,
  Celery + Redis, simplejwt, drf-spectacular, pytest + pytest-django + factory_boy, ruff,
  mypy with django-stubs; dependencies locked with `uv`.
- **Web client** (`frontend/`): React 19, TypeScript strict, Vite, TanStack Query,
  react-router, i18next, Vitest + Testing Library, oxlint; dependencies locked with npm;
  API types generated with openapi-typescript. Only `VITE_*` public configuration in the bundle.
- **Configuration**: every setting that differs between environments comes from environment
  variables, documented in a checked-in `.env.example`. Settings modules: `base`, `dev`,
  `test`, `prod`.

## Deployment & Operations

- **Target**: Docker Compose on Coolify (self-hosted). NO AWS services, SDKs, or docs.
- **Routing**: no host ports are published in the production Compose file; the Coolify proxy
  routes by domain. Ports are configured through variables, never hardcoded on the proxy.
- **Health**: every Compose service MUST define a healthcheck. The API exposes liveness and
  readiness endpoints.
- **Backups**: PostgreSQL is backed up on a schedule with retention, configured in the
  production Compose file.
- **Images**: multi-stage builds, non-root user, pinned base and tool versions.

## Development Workflow

- Features flow through spec-kit: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`. Ad-hoc work beyond trivial fixes is discouraged.
- Work happens on a dedicated branch with small, descriptive commits; each completed phase
  ends with a summary commit and an updated `docs/learning/00-indice.md`.
- Ambiguous choices that significantly change the architecture: pick the simplest, most
  conservative option, record it in an ADR, and continue.

## Governance

This constitution supersedes ad-hoc practices when they conflict. Amendments go through
`/speckit-constitution`, require a stated rationale, and bump the version per semantic
versioning (MAJOR: principle removed or redefined incompatibly; MINOR: principle added or
materially expanded; PATCH: wording). Every change is self-reviewed against Principles I, III,
and V before it is considered done; violations are fixed or justified in the plan's
Complexity Tracking table.

**Version**: 3.1.1 | **Ratified**: 2026-09-17 | **Last Amended**: 2026-11-12
