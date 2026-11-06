# Research: Domain Integrity (Phase 2)

## Where to enforce "no overlapping lessons"
- **Decision**: PostgreSQL `EXCLUDE USING gist` constraints, one per teacher and one per
  student, over `tstzrange(start_time, end_time)` with `&&`, partial on active statuses.
  ADR-009.
- **Rationale**: only the database sees all concurrent transactions; an application check
  ("SELECT overlapping, then INSERT") has a race window between the two statements.
- **Alternatives**: application check only (race); check + `SELECT ... FOR UPDATE` on the
  teacher row (serialises all bookings of a teacher, still misses the student rule unless
  both rows are locked in a fixed order); SERIALIZABLE isolation (retries everywhere);
  unique constraint on start slot (only works with fixed slots).

## Why a stored `end_time`
- **Decision**: store `end_time`; drop the `duration_minutes` column; keep
  `duration_minutes` in the API as a derived field.
- **Rationale**: verified on PostgreSQL 16: `timestamptz + interval` is `STABLE`
  (`provolatile = 's'`), and an index expression `tstzrange(a, a + make_interval(mins => m))`
  fails with "functions in index expression must be marked IMMUTABLE". A stored column is the
  only portable option. One source of truth avoids drift between two columns.
- **Alternatives**: `GeneratedField` (same immutability problem); keep both columns
  (two sources of truth); `timestamp without time zone` (loses the instant, DST bugs).

## Mapping the violation to HTTP
- **Decision**: services run inserts/updates in `transaction.atomic()` (a savepoint inside
  the request transaction), catch `IntegrityError`, read the constraint name from
  `exc.__cause__.diag.constraint_name` (psycopg 3), raise `LessonOverlapError`; the exception
  handler maps `DomainConflict` subclasses to 409 `{"detail", "code"}`.
- **Alternatives**: pre-check query for a nicer message plus the constraint as backstop
  (two code paths for one rule); 400 (409 is the standard for state conflicts).

## Tenant model
- **Decision**: `Studio` is the tenant; mandatory on `Teacher` and `Student`; lessons,
  packages and payments reach it through `student`. ADR-010.
- **Rationale**: Student is the aggregate root of all family data; one denormalised FK there
  gives a direct tenant filter without spreading consistency rules over four tables.
- **Alternatives**: `studio_id` on every table (fast filters, but four places to keep
  consistent — maybe later if profiling asks for it); schema-per-tenant (django-tenants:
  migrations × tenants, overkill for 1–10-teacher studios); database-per-tenant; PostgreSQL
  Row Level Security (strongest guarantee, but needs the tenant in every DB session —
  revisit in phase 4).

## Tenant resolution
- **Decision**: `get_tenant(request)` builds a frozen `TenantContext` with one query (teacher
  or parent profile) and caches it on the underlying `HttpRequest`.
- **Rationale**: JWT authentication happens inside DRF, after middleware, so a middleware
  cannot know the user; caching on the Django request is shared by every DRF wrapper,
  serializer and selector in the same request.
- **Alternatives**: middleware (runs before DRF auth); thread-locals/contextvars (implicit
  global state, leaks between requests if not reset).

## Permissions
- **Decision**: keep role-level `has_permission`, add object-level
  `CanWriteTenantObject.has_object_permission`; reassignment is a dedicated action guarded by
  `IsStudioOwner`. ADR-011.
- **Alternatives**: django-guardian/rules (per-object grants stored in DB — not needed, rules
  derive from the tenant); keep everything in queryset scoping (works for visibility, cannot
  express "visible but not writable").

## Teacher cap under concurrency
- **Decision**: `add_teacher_to_studio` locks the studio row (`select_for_update`) and counts.
- **Alternatives**: trigger with count (DB-level, but logic hidden in SQL); no lock (two
  concurrent joins could make 11).

## Payment state machine
- **Decision**: a dict of allowed transitions in the service; same-status updates allowed.
- **Alternatives**: django-fsm (dependency for three edges); DB trigger.

## API contract
- **Decision**: custom `AutoSchema.get_tags` (app name), a postprocessing hook adding shared
  error components/responses, committed `backend/openapi.yaml`, CI diff. ADR-012.
- **Alternatives**: `@extend_schema(responses=...)` on every view (repetitive, easy to
  forget); schema served only at runtime (no review of contract changes in PRs);
  contract-first (hand-written OpenAPI, then code) — better for multi-team APIs, heavier here.
