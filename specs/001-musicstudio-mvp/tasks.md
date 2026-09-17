# Tasks: MusicStudio MVP — Teacher & Parent Platform

**Input**: Design documents from `/specs/001-musicstudio-mvp/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: INCLUDED — Constitution Principle III mandates tests on package decrement, payment
status transitions, and permission boundaries; the brief also asks for "reasonable test
coverage on the core business logic." Other CRUD surface area is not separately test-tasked.

**Organization**: grouped by user story (spec.md priorities) for independent delivery.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1-US4 map to spec.md's four user stories

## Path Conventions (per plan.md, Option 2: web app)

- Backend: `backend/apps/<app>/...`, Django project config in `backend/config/`
- Frontend: `frontend/src/...`
- Infra: `infra/`

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Create `backend/` and `frontend/` skeletons per plan.md's Project Structure (empty
      app/feature directories, no logic yet)
- [x] T002 Initialize Django project in `backend/config/` (`settings/{base,dev,prod}.py` using
      django-environ for env vars, `urls.py`, `wsgi.py`/`asgi.py`) and `backend/pyproject.toml`
      with Django, djangorestframework, djangorestframework-simplejwt, drf-spectacular,
      django-cors-headers, django-filter, celery, redis, psycopg, pytest-django, factory_boy
- [x] T003 [P] Initialize `frontend/` with Vite + React + TypeScript, add react-router,
      @tanstack/react-query, react-i18next, i18next-browser-languagedetector, vitest,
      @testing-library/react
- [x] T004 [P] Write `infra/docker-compose.yml`, `infra/backend.Dockerfile`,
      `infra/frontend.Dockerfile`, and `infra/.env.example` (db, redis, Django SECRET_KEY, JWT
      signing key, SMTP vars, CORS allowed origins)
- [x] T005 [P] Configure backend linting (ruff) in `backend/pyproject.toml` and frontend
      linting (eslint + prettier) in `frontend/.eslintrc.cjs`

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: no user story work starts until this phase is complete.

- [x] T006 Configure `INSTALLED_APPS`, DRF defaults (pagination, auth classes), CORS, and
      drf-spectacular settings in `backend/config/settings/base.py`
- [x] T007 Custom `User` model (`role`, `email` unique, `preferred_language`) in
      `backend/apps/accounts/models.py`, set `AUTH_USER_MODEL`, initial migration
- [x] T008 [P] JWT auth endpoints (`/auth/token/`, `/auth/token/refresh/`, `/auth/me/`) in
      `backend/apps/accounts/views.py` + `backend/apps/accounts/urls.py`
- [x] T009 [P] Wire drf-spectacular schema/Swagger UI at `/api/schema/` and `/api/docs/` in
      `backend/config/urls.py`
- [x] T010 `Studio` and `Teacher` models + migration in `backend/apps/studios/models.py`
      (`is_owner` requires `studio` set — model-level validation)
- [x] T011 [P] `Student`, `ParentAccount`, and the `ParentStudentLink` through-model +
      migration in `backend/apps/students/models.py`
- [x] T012 Shared queryset-scoping permission classes (`IsTeacherOwner`, `IsStudioOwner`,
      `IsParentOfStudent`, plus a `role_scoped_queryset(user, base_qs, teacher_path,
      studio_path, parent_path)` helper) in `backend/apps/common/permissions.py` — this is the
      single choke point Constitution Principle I's tests target
- [x] T013 Celery app + Celery Beat schedule skeleton in `backend/config/celery.py`, wired to
      Redis via env vars
- [x] T014 [P] Frontend auth: JWT storage/refresh + role-based route guards in
      `frontend/src/auth/AuthProvider.tsx` and `frontend/src/auth/RequireRole.tsx`
- [x] T015 [P] Frontend i18n bootstrap with `frontend/src/i18n/en.json`,
      `frontend/src/i18n/it.json` (nav/dashboard strings from `design/reference/*.dc.html`),
      `frontend/src/i18n/index.ts`
- [x] T016 [P] Frontend theme: CSS custom properties (light + `[data-theme="dark"]`) from
      `design/tokens.md` in `frontend/src/theme/tokens.css`, `frontend/src/theme/ThemeProvider.tsx`
- [x] T017 [P] Frontend typed API client base (fetch wrapper, auth header injection, error
      shape) in `frontend/src/api/client.ts`

**Checkpoint**: foundation ready — user stories can now proceed.

---

## Phase 3: User Story 1 - Teacher runs their week and completes lessons (Priority: P1) 🎯 MVP

**Goal**: teacher dashboard (week view, upcoming 3, counts) + mark-lesson-complete flow that
correctly and idempotently decrements the linked package.

**Independent Test**: per quickstart.md "Validate User Story 1" — log in as teacher, view
dashboard, complete a lesson with a note, confirm exactly one decrement even on retry.

### Tests for User Story 1

- [x] T018 [P] [US1] Test `Lesson.mark_completed()` decrements `Package.lessons_remaining`
      exactly once, is a no-op on a second call, and never decrements on
      cancel/no-show, in `backend/apps/lessons/tests/test_completion.py`
- [x] T019 [P] [US1] Test lesson-completion endpoint permission boundaries (a teacher cannot
      complete another teacher's lesson; studio_owner can complete any lesson in their studio)
      in `backend/apps/lessons/tests/test_permissions.py`

### Implementation for User Story 1

- [x] T020 [P] [US1] `Package` model (fields + computed `status`, `is_low` property, DB
      `CheckConstraint` for `0 <= lessons_remaining <= total_lessons`) + migration in
      `backend/apps/packages/models.py`
- [x] T021 [US1] `Lesson` model with `mark_completed()`/`cancel()` methods (atomic,
      `select_for_update`, idempotency guard) + migration in `backend/apps/lessons/models.py`
      (depends on T020)
- [x] T022 [US1] `LessonSerializer` + `LessonCompleteSerializer` in
      `backend/apps/lessons/serializers.py`
- [x] T023 [US1] `LessonViewSet` (role-scoped queryset via T012 helper, `complete`/`cancel`
      actions, `?week=` filter) in `backend/apps/lessons/views.py`
- [x] T024 [US1] `DashboardView` (week lessons, upcoming 3, pending_payments_count,
      active_students_count, low_package_students) in `backend/apps/lessons/views.py`
- [x] T025 [US1] URL routing for lessons + dashboard in `backend/apps/lessons/urls.py`,
      registered in `backend/config/urls.py`
- [x] T026 [US1] Teacher dashboard page (weekly calendar grid, stat counters, upcoming-3 list)
      matching `design/reference/MusicStudio.dc.html` in
      `frontend/src/features/teacher/Dashboard.tsx`
- [x] T027 [US1] Lesson-complete action + progress-note modal in
      `frontend/src/features/teacher/LessonCompleteModal.tsx`
- [x] T028 [US1] TanStack Query hooks for dashboard/lessons (with cache invalidation on
      complete) in `frontend/src/features/teacher/api/lessons.ts`

**Checkpoint**: teacher can log in, see their week, complete a lesson, package count updates.

---

## Phase 4: User Story 2 - Teacher manages students, packages, and payments (Priority: P1)

**Goal**: roster with package/payment status, student detail view, manual payment
registration.

**Independent Test**: per quickstart.md "Validate User Story 2".

### Tests for User Story 2

- [x] T029 [P] [US2] Test payment creation rejects a `package`/`student` mismatch (400) and
      payment status transitions (pending→paid/overdue) in
      `backend/apps/payments/tests/test_payments.py`
- [x] T030 [P] [US2] Test roster/student-detail endpoint scoping (teacher sees only own
      students; studio_owner sees studio-wide) in
      `backend/apps/students/tests/test_permissions.py`

### Implementation for User Story 2

- [x] T031 [P] [US2] `Payment` model + migration in `backend/apps/payments/models.py`
- [x] T032 [US2] `PackageSerializer`/`PackageViewSet` (create = renewal action) in
      `backend/apps/packages/serializers.py`, `backend/apps/packages/views.py` (depends on T020)
- [x] T033 [US2] `StudentSerializer` (nested `active_package` + payment status) and
      `StudentViewSet` (role-scoped via T012, `/students/{id}/lessons/`) in
      `backend/apps/students/serializers.py`, `backend/apps/students/views.py`
- [x] T034 [US2] `PaymentSerializer`/`PaymentViewSet` (mismatch validation from T029) in
      `backend/apps/payments/serializers.py`, `backend/apps/payments/views.py`
- [x] T035 [US2] URL routing for students/packages/payments in `backend/apps/students/urls.py`,
      `backend/apps/packages/urls.py`, `backend/apps/payments/urls.py`
- [x] T036 [US2] Roster page (table: student, package, remaining, payment status, low-package
      flag) in `frontend/src/features/teacher/Roster.tsx`
- [x] T037 [US2] Student detail page (lesson history, attendance, notes, package/renewal) in
      `frontend/src/features/teacher/StudentDetail.tsx`
- [x] T038 [US2] Payments list + "register payment" form in
      `frontend/src/features/teacher/Payments.tsx`
- [x] T039 [US2] TanStack Query hooks for students/packages/payments in
      `frontend/src/features/teacher/api/{students,packages,payments}.ts`

**Checkpoint**: US1 + US2 both work independently — full teacher-side loop complete.

---

## Phase 5: User Story 3 - Parent checks on their child in isolation (Priority: P2)

**Goal**: read-only parent portal strictly scoped to linked students.

**Independent Test**: per quickstart.md "Validate User Story 3" — including the direct-API
cross-family access attempt (must 404).

### Tests for User Story 3

- [x] T040 [P] [US3] Test parent-role queryset scoping across Student/Lesson/Package/Payment
      viewsets: linked students visible, non-linked student ID returns 404, multi-student
      (sibling) parents see only their own, and every write attempt as parent returns 403, in
      `backend/apps/students/tests/test_parent_scoping.py`

### Implementation for User Story 3

- [x] T041 [US3] Extend `get_queryset()` on Student/Lesson/Package/Payment ViewSets with the
      parent branch of the T012 scoping helper in `backend/apps/students/views.py`,
      `backend/apps/lessons/views.py`, `backend/apps/packages/views.py`,
      `backend/apps/payments/views.py` (depends on T023, T033, T032, T034)
- [x] T042 [US3] Parent portal shell + route guard (parent role only, no write controls
      rendered) in `frontend/src/features/parent/ParentPortal.tsx`
- [x] T043 [US3] Parent views: upcoming lessons, attendance history, payment status (read-only)
      in `frontend/src/features/parent/{UpcomingLessons,Attendance,PaymentStatus}.tsx`
- [x] T044 [US3] Student switcher for parents linked to multiple students in
      `frontend/src/features/parent/StudentSwitcher.tsx`

**Checkpoint**: parent portal is isolated and read-only; all three delivered stories compose.

---

## Phase 6: User Story 4 - Automated reminders and low-package warnings (Priority: P3)

**Goal**: Celery Beat sweep sends a 24h-before reminder to the linked parent (idempotent, no
reminder for cancelled lessons); low-package warning already surfaces via US1/US2 dashboards
and roster (see T024/T036) — this phase wires the automation, not the UI flag.

**Independent Test**: per quickstart.md "Validate User Story 4".

### Tests for User Story 4

- [x] T045 [P] [US4] Test the reminder sweep task: sends exactly once for a lesson in the
      24h window, is idempotent on re-run (`reminder_sent_at` guard), and skips
      cancelled/no_show lessons, in `backend/apps/notifications/tests/test_reminders.py`

### Implementation for User Story 4

- [x] T046 [US4] `send_lesson_reminders` Celery task (query window, render email, stamp
      `reminder_sent_at`) in `backend/apps/notifications/tasks.py` (depends on T021)
- [x] T047 [US4] Register the task on Celery Beat's schedule (every 15 min) in
      `backend/config/celery.py`
- [x] T048 [US4] Bilingual reminder email template (uses recipient's `preferred_language`) in
      `backend/apps/notifications/templates/reminder_email.txt`

**Checkpoint**: all four user stories independently functional — MVP complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T049 `seed_demo` management command (solo teacher, studio_owner + 2 teachers, students
      with packages incl. one low-package, one parent linked to one student, one lesson ~24h
      out) in `backend/apps/common/management/commands/seed_demo.py` — required by
      quickstart.md
- [x] T050 [P] `infra/aws/README.md`: ECS Fargate deployment (task defs, RDS, ElastiCache) as
      primary path + documented EC2 + Docker Compose fallback
- [x] T051 [P] Root `README.md`: local dev quickstart, architecture summary, links to
      `specs/001-musicstudio-mvp/` artifacts
- [x] T052 Finalize `infra/.env.example` against everything actually read by
      `backend/config/settings/*.py` and `frontend/` build
- [x] T053 [P] Basic accessibility pass on teacher/parent UI (keyboard nav, focus states,
      color-contrast check against `design/tokens.md` dark theme) across
      `frontend/src/features/**`
- [x] T054 [P] Frontend Vitest smoke tests for Dashboard, Roster, and ParentPortal render
      paths in `frontend/src/features/**/*.test.tsx`
- [ ] T055 Run `specs/001-musicstudio-mvp/quickstart.md` end-to-end against the Docker Compose
      stack and fix any drift found — **blocked**: this environment has no Docker access
      (WSL without Docker Desktop integration); everything short of `docker compose up`
      itself was verified via sqlite (migrations, `seed_demo`, all 26 backend tests, `ruff`,
      OpenAPI schema generation, an `APIClient` smoke walkthrough) — see the note at the top
      of `quickstart.md`. Run this task from a machine with Docker to close the loop.
- [x] T056 `.gitignore` review (env files, `__pycache__`, `node_modules`, build output) at
      repo root

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → no dependencies
- **Foundational (Phase 2)** → depends on Setup; BLOCKS every user story
- **US1 (Phase 3, P1)** → depends on Foundational only
- **US2 (Phase 4, P1)** → depends on Foundational only (independent of US1, though both P1)
- **US3 (Phase 5, P2)** → depends on Foundational + the ViewSets US1/US2 create (T023, T033,
  T032, T034) since it extends their `get_queryset()`
- **US4 (Phase 6, P3)** → depends on Foundational + `Lesson` model (T021)
- **Polish (Phase 7)** → depends on all four stories (seed_demo touches every entity)

### Parallel Opportunities

- T003-T005 (Setup) in parallel once T001/T002 land
- T008-T009, T011, T014-T017 (Foundational) in parallel once T006/T007/T010/T012 land
- T018-T019 (US1 tests) in parallel; T020 in parallel with nothing (blocks T021)
- T029-T030 (US2 tests) in parallel; T031 in parallel with T020-family work
- US1 and US2 implementation can proceed in parallel (different apps/files) once Foundational
  is done — both are P1 and independent per spec.md
- US3 must wait for the specific ViewSet files from US1/US2 to exist (not fully parallel)
- US4 only needs the `Lesson` model (T021) from US1, not the rest of US1/US2 — can start early
  in parallel with US2

---

## Implementation Strategy

### MVP First

1. Phase 1 → Phase 2 → Phase 3 (US1) → **STOP, validate** (quickstart.md US1 section) →
   demoable: teacher week + lesson completion with correct package decrement.

### Incremental Delivery

2. Add US2 → validate → full teacher-side loop (roster/detail/payments) demoable.
3. Add US3 → validate → parent portal isolation demoable (the highest-trust-risk story).
4. Add US4 → validate → reminders demoable → Polish phase → done.
