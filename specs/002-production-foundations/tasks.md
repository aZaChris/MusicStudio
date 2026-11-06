# Tasks: Production Foundations (Phase 1)

**Input**: Design documents from `specs/002-production-foundations/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-changes.md

**Tests**: REQUIRED by the constitution (Principle III). Every story ships tests, including
cross-tenant read/write tests and query-count assertions. Every story ships its ADR/study-doc
tasks (Principle VIII).

**Paths**: backend code under `backend/`, study docs under `docs/learning/`.

## Phase 1: Setup

- [X] T001 Upgrade to Django 5.2 LTS and add whitenoise in `backend/pyproject.toml`; refresh `backend/uv.lock`
- [X] T002 Add dev tools (mypy, django-stubs, djangorestframework-stubs, pytest-cov, pre-commit) and their config (`[tool.mypy]`, `[tool.django-stubs]`, `[tool.coverage]`, pytest addopts, ruff rule set) in `backend/pyproject.toml`
- [X] T003 Make the existing code pass mypy (annotations in `backend/apps/**`, `backend/config/**`)

## Phase 2: Foundational (blocks all stories)

- [X] T004 Split settings: `backend/config/settings/base.py` (env-driven: cache, throttling, logging, CSRF origins, admin URL, Celery result backend), `dev.py`, new `test.py`, `prod.py` (fail-fast, proxy SSL header, HSTS, whitenoise storage); point pytest at `config.settings.test`
- [X] T005 Create root `.env.example` documenting every variable for dev and production; delete `infra/.env.example`
- [X] T006 [P] Create `backend/apps/common/scoping.py` (move `role_scoped_queryset` from `backend/apps/common/permissions.py`, add `students_visible_to`, `packages_visible_to`) and `backend/apps/common/serializers.py` (`ScopedRelatedFieldsMixin`)

## Phase 3: User Story 1 — Scoped writes (P1) 🎯 MVP

**Goal**: no write can reference another tenant's student or package.
**Independent test**: `pytest -k cross_tenant` — every attempt returns 400 and writes nothing.

- [X] T007 [P] [US1] Cross-tenant write tests for lessons (create, re-assign student, foreign package) in `backend/apps/lessons/tests/test_cross_tenant_writes.py`
- [X] T008 [P] [US1] Cross-tenant write tests for payments and packages in `backend/apps/payments/tests/test_cross_tenant_writes.py` and `backend/apps/packages/tests/test_cross_tenant_writes.py`
- [X] T009 [US1] Apply `ScopedRelatedFieldsMixin` to `backend/apps/lessons/serializers.py`, `backend/apps/payments/serializers.py`, `backend/apps/packages/serializers.py`
- [X] T010 [US1] Lesson write use-cases (`create_lesson`, `update_lesson`, `complete_lesson`, `cancel_lesson`, package-belongs-to-student rule) in `backend/apps/lessons/services.py`; remove `mark_completed`/`cancel` from `backend/apps/lessons/models.py`; views call services
- [X] T011 [US1] Payment rule `ensure_package_matches_student` and `create_payment`/`update_payment` in `backend/apps/payments/services.py`; model `clean()` reuses it, `save()` override removed
- [X] T012 [US1] Student creation in `backend/apps/students/services.py`; adapt existing tests in `backend/apps/lessons/tests/test_completion.py` to the services

## Phase 4: User Story 2 — Constant query counts (P1)

**Goal**: list/dashboard cost independent of row count.
**Independent test**: `pytest -k num_queries` with 1 and 25 rows.

- [X] T013 [P] [US2] Query-budget tests for students, lessons, packages, payments, dashboard, studio teachers in `backend/apps/common/tests/test_num_queries.py`
- [X] T014 [US2] `students_for(user)` with `Prefetch(to_attr)` + latest-payment `Subquery` in `backend/apps/students/selectors.py`; `StudentSerializer` reads annotations
- [X] T015 [US2] `lessons_for`, `upcoming_lessons_for`, `dashboard_for` (single annotated low-package query) in `backend/apps/lessons/selectors.py`; thin `DashboardView`
- [X] T016 [US2] `packages_for`, `payments_for` in `backend/apps/packages/selectors.py`, `backend/apps/payments/selectors.py`; `studio_for_owner` with annotated `teacher_count` in `backend/apps/studios/selectors.py`
- [X] T017 [US2] Indexes and `Teacher` owner CheckConstraint (data-model.md) in models + migrations `backend/apps/{lessons,payments,packages,studios}/migrations/`

## Phase 5: User Story 3 — Edge inputs (P2)

**Independent test**: package without remaining count → 201; invalid week → 400; ownerless studio → 404.

- [X] T018 [P] [US3] Tests in `backend/apps/packages/tests/test_packages.py`, `backend/apps/lessons/tests/test_week_param.py`, `backend/apps/studios/tests/test_studio.py`
- [X] T019 [US3] `create_package` in `backend/apps/packages/services.py`; `lessons_remaining` read-only in `backend/apps/packages/serializers.py`
- [X] T020 [US3] Week parsing with 400 in `backend/apps/lessons/selectors.py`; studio views 404 in `backend/apps/studios/views.py`

## Phase 6: User Story 4 — Operable deployment (P1)

**Independent test**: quickstart.md §4–§6.

- [X] T021 [P] [US4] Health tests (live, ready ok, ready 503 on DB/Redis failure, HTTPS-redirect exemption) in `backend/config/tests/test_health.py`
- [X] T022 [US4] Health views in `backend/config/health.py`, routes in `backend/config/urls.py` (+ env admin URL)
- [X] T023 [P] [US4] Settings tests (prod fails without secrets, proxy SSL header) in `backend/config/tests/test_settings.py`
- [X] T024 [US4] Multi-stage non-root `backend/Dockerfile`, `backend/.dockerignore`, `backend/docker/entrypoint.sh`, `backend/docker/healthcheck.py`
- [X] T025 [US4] Dev stack `docker-compose.yml` (healthchecks on all services, frontend behind `frontend` profile); delete `infra/docker-compose.yml`, `infra/backend.Dockerfile`
- [X] T026 [US4] Coolify stack `docker-compose.coolify.yml` (no ports, `${VAR:?}`, healthchecks, backup sidecar)
- [X] T027 [US4] Remove AWS: delete `infra/aws/`, rewrite `README.md` deploy/stack sections, add historical notes to `specs/001-musicstudio-mvp/{plan,research,tasks}.md`
- [X] T028 [US4] `seed_demo` refuses to run with `DEBUG=False` unless `--force` in `backend/apps/common/management/commands/seed_demo.py` (+ test)

## Phase 7: User Story 5 — Login throttling (P2)

- [X] T029 [P] [US5] Throttle tests in `backend/apps/accounts/tests/test_auth.py` (token obtain/refresh, `me`, 429 after limit)
- [X] T030 [US5] Throttled token view in `backend/apps/accounts/views.py`, `backend/apps/accounts/urls.py`

## Phase 8: User Story 6 — Reminders at most once (P2)

- [X] T031 [P] [US6] Overlap test (claimed lesson is skipped by a second sweep) and query-count test in `backend/apps/notifications/tests/test_reminders.py`
- [X] T032 [US6] `send_due_reminders` with claim-then-send in `backend/apps/notifications/services.py`; `shared_task` wrapper in `backend/apps/notifications/tasks.py`

## Phase 9: User Story 7 — Quality gate (P1)

- [X] T033 [P] [US7] `.github/workflows/ci.yml` (Postgres 16 + Redis 7 services, ruff, format, mypy, migrations check, pytest --cov)
- [X] T034 [P] [US7] `.pre-commit-config.yaml` (hygiene hooks, ruff, ruff-format, mypy, detect-private-key)

## Phase 10: User Story 8 — Study documentation (P2)

- [ ] T035 [P] [US8] ADR-002…ADR-008 in `docs/learning/adr/`
- [ ] T036 [P] [US8] `docs/learning/01-panoramica-architettura.md`
- [ ] T037 [P] [US8] Concept docs in `docs/learning/concetti/` (service layer, N+1, indici/EXPLAIN, BOLA/isolamento, configurazione per ambienti, strategia di test, CI, Docker/Coolify, health check e backup, rate limiting)
- [ ] T038 [P] [US8] `docs/learning/glossario.md`, `docs/learning/colloquio/domande-e-risposte.md`
- [ ] T039 [US8] `docs/learning/00-indice.md` with reading order

## Phase 11: Polish & Cross-Cutting

- [ ] T040 OWASP API Security Top 10 walk for phase 1 in `docs/learning/concetti/sicurezza-api-owasp.md`
- [ ] T041 Full gate run (ruff, mypy, migrations check, pytest ≥ 90%); update `README.md`; phase 1 summary commit

## Dependencies

- Setup (T001–T003) → Foundational (T004–T006) → stories.
- US1 before US2 (both edit the same serializers/views); US3 after US2 (selectors exist).
- US4, US5, US6, US7 independent of each other after Foundational.
- US8 after the code it documents; T040–T041 last.

## Parallel examples

- US1: T007 and T008 together (different test files).
- After Foundational: US4 (T024–T027), US7 (T033–T034) and US6 (T031–T032) in parallel.
- US8: T035–T038 all in parallel.

## Implementation strategy

MVP = US1 (closes the verified security hole). Then US2 (performance), US4 + US7 (operability
and gate), then the P2 stories, docs, and the final gate run. Commit after each story.
