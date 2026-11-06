# Implementation Plan: Production Foundations (Phase 1)

**Branch**: `refactor/production-standards` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-production-foundations/spec.md`

## Summary

Bring the existing Django backend (restored from `4be062d`, ADR-001) to production standard:
close the cross-tenant write hole by scoping serializer related fields; move business logic
into `services.py`/`selectors.py` per app and remove N+1 with prefetch/subquery annotations
pinned by query-count tests; split settings into dev/test/prod driven by env vars; add
health endpoints, throttling, indexes, Django 5.2 LTS; replace AWS with a Coolify Compose
stack (healthchecks everywhere, no published ports, scheduled pg backups); add GitHub Actions
CI and pre-commit; produce the Italian study docs. Phases 2–5 are a roadmap (below).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.2 LTS, Django REST Framework 3.17, simplejwt,
drf-spectacular, django-filter, django-cors-headers, django-environ, Celery 5.6, redis-py,
psycopg 3, gunicorn, whitenoise

**Storage**: PostgreSQL 16; Redis 7 (Celery broker/results, Django cache for throttling)

**Testing**: pytest, pytest-django, factory_boy, pytest-cov (fail under 90%),
`django_assert_num_queries` for query budgets

**Tooling**: uv (lockfile), ruff (lint + format), mypy + django-stubs +
djangorestframework-stubs, pre-commit, GitHub Actions

**Target Platform**: Linux containers; Docker Compose locally; Coolify (self-hosted) in
production, TLS terminated by Coolify's proxy

**Project Type**: web service (API-only backend); `frontend/` exists but is out of scope

**Performance Goals**: constant query count per list endpoint; readiness check < 1 s

**Constraints**: no AWS; no published host ports in production; every config via env vars;
healthcheck on every service; frontend untouched

**Scale/Scope**: studios of 1–10 teachers, hundreds of students per studio

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] I. Reads AND writes scoped per tenant; cross-tenant read/write tests planned (US1)
- [x] II. Feature reachable via `/api/v1/`, OpenAPI accurate (no endpoint removed; health is
  infrastructure, outside `/api/v1/`)
- [x] III. Tests in the same change; query-count assertions on main endpoints (US2)
- [x] IV. Within phase 1 of the roadmap
- [x] V. Logic moved into `services.py` / `selectors.py`; mypy added and clean
- [x] VI. No client code modified (`frontend/` untouched; dev compose puts it behind a profile)
- [x] VII. CI added in this feature (US7)
- [x] VIII. ADR-002…ADR-008 and study docs planned (US8)
- [x] IX. OWASP API Top 10 walk recorded at the end of the phase

Post-design re-check: still passing; no Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-production-foundations/
├── plan.md              # this file
├── research.md          # decisions and rejected alternatives
├── data-model.md        # index/constraint changes (no new entities)
├── quickstart.md        # validation guide
├── contracts/api-changes.md
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
backend/
├── Dockerfile                 # multi-stage, non-root, healthcheck (replaces infra/backend.Dockerfile)
├── docker/entrypoint.sh       # web: migrate (opt-in) then gunicorn; worker; beat
├── docker/healthcheck.py      # stdlib-only health probes (http, beat schedule freshness)
├── config/settings/{base,dev,test,prod}.py
├── config/health.py           # /health/live/, /health/ready/
└── apps/<domain>/
    ├── models.py              # data, constraints, indexes, trivial properties
    ├── services.py            # write use-cases
    ├── selectors.py           # scoped/prefetched reads
    ├── serializers.py, views.py, urls.py
    └── tests/
docker-compose.yml             # dev: db, redis, backend, worker, beat (+ frontend profile)
docker-compose.coolify.yml     # prod: no ports, healthchecks, required vars, backup service
.env.example                   # every variable, documented
.github/workflows/ci.yml       # ruff, mypy, migrations check, pytest+coverage
.pre-commit-config.yaml
docs/learning/                 # Italian study docs (index, overview, ADRs, concepts, glossary, Q&A)
infra/frontend.Dockerfile      # kept as-is for the isolated frontend (only file left in infra/)
```

**Structure Decision**: keep the existing `backend/apps/<domain>` modular monolith; add
`services.py`/`selectors.py` per domain (ADR-002). Compose files move to the repo root so
Coolify can point at them directly; AWS docs are deleted (ADR-003).

## Implementation approach (by user story)

- **US1 scoped writes**: `apps/common/serializers.py` mixin restricts `student`/`package`
  querysets to `students_visible_to(user)` / `packages_visible_to(user)`; lesson package must
  belong to the lesson's student (found during design: same-teacher cross-student package).
- **US2 N+1**: `students.selectors.students_for(user)` annotates `latest_payment_status`
  (Subquery) and prefetches active packages (`Prefetch(..., to_attr=...)`);
  `lessons.selectors.dashboard_for(user)` computes low-package students with one annotated
  query; `StudioSerializer.teacher_count` via `annotate(Count)`; reminders prefetch parents.
- **US3 edge inputs**: package service sets `lessons_remaining`; field read-only; week param
  parsed in selector → `ValidationError`; studio views 404 without profile.
- **US4 ops**: settings split, prod fail-fast (`env()` without default), proxy SSL header,
  CSRF trusted origins, whitenoise for admin static, health endpoints, Compose files, backup
  sidecar, AWS removal.
- **US5 throttling**: DRF `AnonRateThrottle`/`UserRateThrottle` + `ScopedRateThrottle` on the
  token view; cache on Redis (locmem in tests).
- **US6 reminders**: claim each lesson with a conditional `UPDATE … WHERE reminder_sent_at IS
  NULL` before sending (at-most-once), `shared_task`, logic in `notifications/services.py`.
- **US7 CI**: one workflow, Postgres + Redis service containers, `uv sync --frozen`.
- **US8 docs**: see `docs/learning/00-indice.md`.

## Roadmap: phases 2–5 (not implemented in this feature)

Each phase is specified with its own `/speckit-specify` run, ends with an OWASP API Top 10
walk, a summary commit, and an updated `docs/learning/00-indice.md`.

### Phase 2 — Domain
- Lesson scheduling without overlaps: PostgreSQL `ExclusionConstraint` (btree_gist,
  `tstzrange(start, end)` with `&&`, per teacher, excluding cancelled lessons); API returns
  409/400 with a clear message.
- Explicit multi-tenancy: a `Studio` as tenant for every teacher (solo teacher = studio of
  one), tenant FK denormalised on hot tables, scoping by tenant instead of role branches.
- DRF permissions as object-level classes per action; studio-owner management of teachers.
- OpenAPI polish: examples, error schemas, operation ids, schema diff check in CI.
- Concepts: ExclusionConstraint, multi-tenancy, permessi DRF, OpenAPI.

### Phase 3 — Celery & payments
- Celery hardening: idempotent tasks with idempotency keys, retries with backoff, acks_late,
  dead-letter handling, beat schedule in DB if needed.
- Stripe **test mode**: Checkout for packages, idempotent webhook endpoint (signature check,
  event-id dedup table, transactional state change), reconciliation task.
- Caching: per-user dashboard cache with explicit invalidation.
- Concepts: task Celery idempotenti, webhook idempotenti, caching.

### Phase 4 — Production
- Real Coolify deployment, domains, secrets; off-site backup copy and a tested restore drill.
- Sentry (errors + performance), structured JSON logs with request ids.
- Load tests with Locust on roster/dashboard/login; p95 targets recorded.
- Full OWASP API Security Top 10 checklist.
- Concepts: osservabilità, deploy con Coolify, test di carico, sicurezza API.

### Phase 5 — Polish
- API versioning policy, deprecation headers, pagination tuning, admin hardening, data
  retention/GDPR export, README and portfolio write-up, final interview Q&A pass.

## Complexity Tracking

No violations to justify.
