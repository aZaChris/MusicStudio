# Phase 1 Contracts: REST API surface

> **Amended 2026-09-17**: rebuilt as Next.js Route Handlers under `app/api/v1/*` (see
> research.md, plan.md). Below reflects what's actually implemented; a couple of endpoints from
> the original Django-era contract (PATCH on students/lessons, a studio summary endpoint) were
> not carried over — noted as follow-ups at the bottom, not silently dropped.

Base path: `/api/v1/`. This document is the human contract the frontend and tasks.md are
planned against.

Auth is Auth.js (`next-auth`), not a custom token endpoint: `POST /api/auth/callback/credentials`
(email+password, handled by the Credentials provider) sets a session cookie; `GET/POST
/api/auth/[...nextauth]` covers the rest of the Auth.js surface (CSRF token, session, sign-out).
All `/api/v1/*` routes require an authenticated session and return **scoped** results per the
rules in `data-model.md`/`lib/rbac.ts` — a 404 (not 403) for an out-of-scope object ID, so
existence of other families' records is never leaked.

## Students

| Method | Path | Notes |
|---|---|---|
| GET | `/students/` | teacher: own students; studio_owner: studio's students; parent: linked students. `?is_active=false` includes inactive |
| POST | `/students/` | teacher/studio_owner only |
| GET | `/students/{id}/` | detail incl. nested `activePackage` summary |
| GET | `/students/{id}/lessons/` | lesson history for that student (attendance + notes) |

## Packages

| Method | Path | Notes |
|---|---|---|
| GET | `/packages/?student={id}` | scoped per role |
| POST | `/packages/` | teacher/studio_owner only — creates a new package (renewal) for a student |

## Lessons

| Method | Path | Notes |
|---|---|---|
| GET | `/lessons/?week=` | teacher: own lessons for the given week (defaults to current); studio_owner: studio-wide; parent: their students' lessons only |
| GET | `/lessons/upcoming/` | next 3 upcoming lessons for the requesting teacher (dashboard widget) |
| POST | `/lessons/{id}/complete/` | body: `{ "note"?: string }` → sets status=completed, decrements linked package (idempotent, see research.md). Teacher/studio_owner only, own lesson only |
| POST | `/lessons/{id}/cancel/` | body: `{ "status": "cancelled" \| "no_show" }` — no package side-effect |

## Payments

| Method | Path | Notes |
|---|---|---|
| GET | `/payments/?status=` | scoped per role (parent: read-only, own students' payments only) |
| POST | `/payments/` | teacher/studio_owner only. Validates `package.studentId === studentId` (400 on mismatch) |
| PATCH | `/payments/{id}/` | status transitions (pending → paid/overdue) — teacher/studio_owner only |

## Dashboard aggregate

| Method | Path | Notes |
|---|---|---|
| GET | `/dashboard/` | `{ week, upcoming, pendingPaymentsCount, activeStudentsCount, lowPackageStudents }`, role-scoped |

## Follow-ups not carried over from the original contract (not silently dropped)

- `PATCH /students/{id}/`, `PATCH /lessons/{id}/` (reschedule) — no UI need surfaced them yet;
  add when a "reschedule"/"edit student" flow is requested.
- Studio summary (`GET /studio/`, `GET /studio/teachers/`) — a studio_owner already sees
  studio-wide data through the scoped student/lesson/payment endpoints above; a dedicated
  studio/teacher-roster view is a small addition, not blocked by anything, just not built yet.

## Permission matrix (enforced in `lib/rbac.ts` + `lib/api-helpers.ts`, tested per Constitution Principle I)

| Endpoint group | teacher | studio_owner | parent |
|---|---|---|---|
| own resources (students/lessons/packages/payments they own) | read/write | read/write (studio-wide) | — |
| other teacher's resources within same studio | — | read/write | — |
| linked students' resources | — | — | read-only |
| any other family's resources | 404 | 404 (outside studio) | 404 |
| write anything as parent | n/a | n/a | 403 (always) |
