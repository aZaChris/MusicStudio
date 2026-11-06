# Implementation Plan: Domain Integrity (Phase 2)

**Branch**: `refactor/production-standards` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-domain-integrity/spec.md`

## Summary

Make the domain rules guarantees instead of conventions. Lessons get a stored `end_time` and
two PostgreSQL exclusion constraints (per teacher, per student, active statuses only) with
overlap mapped to 409. The studio becomes the explicit tenant: mandatory for teachers and
students, resolved once per request into a `TenantContext` that drives all scoping. Write
permissions become per-object DRF permission classes; owners can reassign students within
their studio; studios are capped at 10 teachers. Payments get a status state machine. The
OpenAPI schema gets domain tags and documented error responses, is committed, and CI diffs it.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.2 LTS (`django.contrib.postgres`: ExclusionConstraint,
BtreeGistExtension, RangeOperators), DRF 3.17, drf-spectacular 0.30 (postprocessing hooks)

**Storage**: PostgreSQL 16 with `btree_gist`

**Testing**: pytest + factory_boy, real PostgreSQL; `TransactionTestCase`-style test with
two threads/connections for the concurrent booking scenario

**Target Platform**: unchanged (Docker Compose on Coolify)

**Project Type**: web service (API-only)

**Performance Goals**: query budgets from phase 1 unchanged or lower

**Constraints**: API keeps `duration_minutes`; no production data yet, migrations may be
strict; `frontend/` untouched

**Scale/Scope**: studios of 1–10 teachers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] I. Reads and writes scoped per tenant; scoping now keyed on an explicit studio tenant;
  phase 1 cross-tenant tests kept + new tests for reassignment
- [x] II. Reachable via `/api/v1/`; OpenAPI improved and committed
- [x] III. Tests in the same change; query budgets re-asserted
- [x] IV. Phase 2 of the roadmap
- [x] V. Logic in services/selectors; tenant resolution in `apps/common/tenancy.py`
- [x] VI. No client code modified
- [x] VII. CI extended with the schema-drift check
- [x] VIII. ADR-009…ADR-012 and four concept docs planned
- [x] IX. OWASP walk updated at end of phase

Post-design re-check: passing. No Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/003-domain-integrity/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/api-changes.md
└── tasks.md
```

### Source Code (changes)

```text
backend/
├── openapi.yaml                       # committed contract (generated)
├── apps/common/tenancy.py             # TenantContext + get_tenant(request), cached per request
├── apps/common/scoping.py             # scoping by TenantContext + per-model tenant paths
├── apps/common/permissions.py         # + object-level CanWriteTenantObject
├── apps/common/exceptions.py          # + DomainConflict → 409
├── apps/common/schema.py              # AutoSchema tags + error-response postprocessing hook
├── apps/studios/{models,services}.py  # mandatory studio, teacher cap, add_teacher_to_studio
├── apps/students/{models,services,views}.py  # studio FK, reassign action
├── apps/lessons/{models,services}.py  # end_time, exclusion constraints, overlap → 409
└── apps/payments/services.py          # status state machine
```

**Structure Decision**: no new apps; tenancy is cross-cutting and lives in `apps/common`.

## Implementation approach

- **Overlap (US1)**: `Lesson.end_time` (stored), `duration_minutes` becomes a property and a
  serializer field converted by the service. Migration: add nullable → backfill with SQL →
  NOT NULL → drop `duration_minutes` → `BtreeGistExtension` → two `ExclusionConstraint`s
  (`lesson_no_teacher_overlap`, `lesson_no_student_overlap`) with
  `condition=Q(status__in=[scheduled, completed])` + CheckConstraint `end_time > start_time`.
  Services wrap writes in `transaction.atomic()` and translate the constraint's
  `IntegrityError` (by constraint name) into `LessonOverlapError(DomainConflict)` → 409.
- **Tenancy (US2)**: data migration gives every solo teacher a personal studio (owner);
  `Teacher.studio` NOT NULL, `on_delete=PROTECT`; `Student.studio` added, backfilled,
  NOT NULL. `TenantContext(role, studio_id, teacher_id, parent_id)` resolved with one query and
  cached on the underlying `HttpRequest`. Scoping takes a context and a `TenantPaths` per model.
- **Permissions (US3)**: `CanWriteTenantObject.has_object_permission` (owner: same studio;
  teacher: own teacher; parent: never). `POST /students/{id}/reassign/` (owner only).
  `studios.services.add_teacher_to_studio` locks the studio row and enforces the cap;
  `Teacher.clean()` reuses it for the admin.
- **Payments (US4)**: `ALLOWED_TRANSITIONS` dict in `payments/services.py`.
- **Contract (US5)**: custom `AutoSchema.get_tags()` (app label), postprocessing hook adding
  `Error`/`ValidationError` components and 400/401/403/404/409/429 responses where relevant;
  `backend/openapi.yaml` committed; CI step regenerates and `diff`s; pre-commit hook too.

## Roadmap

Unchanged from `specs/002-production-foundations/plan.md`: phase 3 Celery & payments, phase 4
production, phase 5 polish.

## Complexity Tracking

No violations to justify.
