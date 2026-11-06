# Tasks: Domain Integrity (Phase 2)

**Input**: `specs/003-domain-integrity/` (plan, spec, research, data-model, contracts)

**Tests**: REQUIRED (Constitution III). Docs/ADR tasks REQUIRED (Constitution VIII).

## Phase 1: Setup

- [X] T001 Add `django.contrib.postgres` to `INSTALLED_APPS` in `backend/config/settings/base.py`

## Phase 2: Foundational (blocks all stories)

- [X] T002 `DomainConflict` exception → 409 `{"detail","code"}` in `backend/apps/common/exceptions.py` (+ test)
- [X] T003 `TenantContext` + `get_tenant(request)` (one query, cached on the HttpRequest) in `backend/apps/common/tenancy.py`

## Phase 3: User Story 2 — Studio as tenant (P1) — done first: US1/US3 build on it

- [X] T004 [US2] Tests: migration result (every teacher/student has a studio), tenant resolution query count, studio invariant on create, in `backend/apps/common/tests/test_tenancy.py`
- [X] T005 [US2] Data migration: personal studios for solo teachers; `Teacher.studio` NOT NULL + PROTECT in `backend/apps/studios/migrations/`
- [X] T006 [US2] `Student.studio` FK + backfill migration in `backend/apps/students/`; `create_student` sets studio from teacher
- [X] T007 [US2] Rewrite `backend/apps/common/scoping.py` around `TenantContext` + per-model `TenantPaths`; selectors/serializer mixin/views take the context
- [X] T008 [US2] Factories: teachers always get a studio, students inherit it, in `backend/apps/common/factories.py`; keep all phase 1 tests green

## Phase 4: User Story 1 — No overlapping lessons (P1) 🎯 MVP

- [X] T009 [P] [US1] Overlap tests (teacher, student, back-to-back, cancelled frees slot, move onto occupied slot, complete a cancelled lesson whose slot was taken, DST-independent) in `backend/apps/lessons/tests/test_overlap.py`
- [X] T010 [P] [US1] Concurrency test: two threads book the same slot, exactly one succeeds, in `backend/apps/lessons/tests/test_overlap_concurrency.py`
- [X] T011 [US1] `Lesson.end_time`, `duration_minutes` property, check + exclusion constraints, `BtreeGistExtension` migration with backfill in `backend/apps/lessons/`
- [X] T012 [US1] Services translate the constraint violation to `LessonOverlapError`; serializer keeps `duration_minutes` and exposes `end_time` in `backend/apps/lessons/{services,serializers}.py`; update reminders/seed/factories

## Phase 5: User Story 3 — Per-object permissions (P2)

- [X] T013 [P] [US3] Tests: reassign (owner same studio OK, other studio 400, teacher 403, parent 403, outside studio 404), teacher cap 10, object permission, in `backend/apps/students/tests/test_reassign.py` and `backend/apps/studios/tests/test_teacher_cap.py`
- [X] T014 [US3] `CanWriteTenantObject` in `backend/apps/common/permissions.py`, applied to student/lesson/package/payment viewsets
- [X] T015 [US3] `reassign_student` service + `POST /students/{id}/reassign/` action
- [X] T016 [US3] `add_teacher_to_studio` (row lock + cap) in `backend/apps/studios/services.py`; `Teacher.clean()` reuses it

## Phase 6: User Story 4 — Payment state machine (P2)

- [X] T017 [P] [US4] Parametrised test over all 9 status pairs in `backend/apps/payments/tests/test_transitions.py`
- [X] T018 [US4] `ALLOWED_TRANSITIONS` in `backend/apps/payments/services.py`

## Phase 7: User Story 5 — API contract (P2)

- [X] T019 [US5] `MusicStudioAutoSchema` (tags) + error-response postprocessing hook in `backend/apps/common/schema.py`; settings wiring
- [X] T020 [US5] Generate and commit `backend/openapi.yaml`; CI diff step in `.github/workflows/ci.yml`; pre-commit hook; schema test

## Phase 8: User Story 6 — Study docs (P2)

- [X] T021 [P] [US6] ADR-009 (exclusion constraint + stored end_time), ADR-010 (studio tenant), ADR-011 (permissions), ADR-012 (committed contract)
- [X] T022 [P] [US6] Concepts: `exclusion-constraint.md`, `multi-tenancy.md`, `permessi-drf.md`, `openapi-e-contratti.md` in `docs/learning/concetti/`
- [X] T023 [US6] Update `glossario.md`, `colloquio/domande-e-risposte.md`, `01-panoramica-architettura.md`, `00-indice.md`, audit addendum if new defects
- [X] T024 [US6] OWASP walk update in `docs/learning/concetti/sicurezza-api-owasp.md`

## Phase 9: Polish

- [ ] T025 Full gate (ruff, mypy, migrations, pytest ≥ 90%, schema diff); README; phase 2 summary commit
- [ ] T026 Copy study docs to `C:\Users\Christian\Documents\doc_music_studio`

## Dependencies

Setup → Foundational → US2 → US1 → (US3, US4, US5 in any order) → US6 → Polish.
US2 goes first despite the spec's numbering: overlap tests and permissions rely on teachers
always having a studio.

## Parallel examples

T009 ∥ T010; T013 ∥ T017; T021 ∥ T022.

## Implementation strategy

Tenancy migration first (riskiest data change), then the overlap constraint (MVP of the
phase), then the smaller rules, contract and docs. Commit after each story.
