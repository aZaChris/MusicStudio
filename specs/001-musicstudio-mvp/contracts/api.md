# Phase 1 Contracts: REST API surface

Base path: `/api/v1/`. Full machine-readable schema is generated at runtime by
drf-spectacular (`/api/schema/`, browsable at `/api/docs/`) — this document is the
human contract the frontend and tasks.md are planned against; it is not meant to be kept
byte-for-byte in sync with the generated schema.

All endpoints require `Authorization: Bearer <JWT>` except auth endpoints. All list endpoints
are paginated (DRF `PageNumberPagination`). All endpoints return **scoped** results per the
queryset rules in `data-model.md` — a 404 (not 403) is returned for an out-of-scope object ID,
so existence of other families' records is never leaked.

## Auth (`apps/accounts`)

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/token/` | obtain access+refresh JWT (email+password) |
| POST | `/auth/token/refresh/` | refresh access token |
| GET | `/auth/me/` | current user: id, email, first_name, last_name, role, `teacher` or `parent_account` sub-profile |

## Studios & Teachers (`apps/studios`) — studio_owner only for studio-wide reads

| Method | Path | Notes |
|---|---|---|
| GET | `/studio/teachers/` | studio_owner: list teachers in their studio. teacher: 403 |
| GET | `/studio/` | studio_owner: their studio's summary (name, teacher count) |

## Students (`apps/students`)

| Method | Path | Notes |
|---|---|---|
| GET | `/students/` | teacher: own students; studio_owner: studio's students; parent: linked students. Supports `?is_active=true` filter |
| POST | `/students/` | teacher/studio_owner only |
| GET | `/students/{id}/` | detail incl. nested `active_package` summary |
| PATCH | `/students/{id}/` | teacher/studio_owner only, own student only |
| GET | `/students/{id}/lessons/` | lesson history for that student (attendance + notes) |

## Packages (`apps/packages`)

| Method | Path | Notes |
|---|---|---|
| GET | `/packages/?student={id}` | scoped per role |
| POST | `/packages/` | teacher/studio_owner only — creates a new package (renewal) for a student |
| GET | `/packages/{id}/` | includes computed `status` |

## Lessons (`apps/lessons`)

| Method | Path | Notes |
|---|---|---|
| GET | `/lessons/?week=` | teacher: own lessons for the given week (defaults to current); studio_owner: studio-wide; parent: their students' lessons only |
| GET | `/lessons/upcoming/` | next 3 upcoming lessons for the requesting teacher (dashboard widget) |
| POST | `/lessons/` | teacher/studio_owner only |
| PATCH | `/lessons/{id}/` | reschedule (start_time/duration) — scheduled lessons only |
| POST | `/lessons/{id}/complete/` | body: `{ "note"?: string }` → sets status=completed, decrements linked package (idempotent, see research.md). Teacher/studio_owner only, own lesson only |
| POST | `/lessons/{id}/cancel/` | body: `{ "status": "cancelled" \| "no_show" }` — no package side-effect |

## Payments (`apps/payments`)

| Method | Path | Notes |
|---|---|---|
| GET | `/payments/?status=` | scoped per role (parent: read-only, own students' payments only) |
| POST | `/payments/` | teacher/studio_owner only. Validates `package.student == student` (400 on mismatch) |
| PATCH | `/payments/{id}/` | status transitions (pending → paid/overdue) — teacher/studio_owner only |

## Dashboard aggregate (`apps/lessons` view, read-only composite)

| Method | Path | Notes |
|---|---|---|
| GET | `/dashboard/` | teacher: `{ week: Lesson[], upcoming: Lesson[3], pending_payments_count, active_students_count, low_package_students: Student[] }` |

## Permission matrix (enforced by DRF permission classes, tested per Constitution Principle I)

| Endpoint group | teacher | studio_owner | parent |
|---|---|---|---|
| own resources (students/lessons/packages/payments they own) | read/write | read/write (studio-wide) | — |
| other teacher's resources within same studio | — | read/write | — |
| linked students' resources | — | — | read-only |
| any other family's resources | 404 | 404 (outside studio) | 404 |
| write anything as parent | n/a | n/a | 403 (always) |
