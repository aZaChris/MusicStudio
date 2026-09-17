# Quickstart: validate MusicStudio MVP end-to-end

## Prerequisites

- Docker + Docker Compose installed.
- `infra/.env` populated from `infra/.env.example` (DB creds, Django `SECRET_KEY`, JWT
  signing key, SMTP settings for reminder emails — console backend is fine locally).

## Bring the stack up

```bash
cd infra
docker compose up --build
```

This starts: `db` (Postgres), `redis`, `backend` (Django on :8000), `celery-worker`,
`celery-beat`, `frontend` (Vite dev server on :5173).

## Seed a demo scenario

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
```

`seed_demo` (a management command, see tasks.md) creates: one solo teacher, one
studio_owner with 2 teachers, a handful of students with active packages (including one at
1 lesson remaining to exercise the low-package warning), one parent account linked to one
student, and one lesson starting ~24h from now on an active student (to exercise the
reminder sweep).

## Validate User Story 1 — teacher week + lesson completion (spec.md US1)

1. Log in at `http://localhost:5173` as the seeded teacher.
2. Confirm the dashboard shows this week's calendar, next 3 upcoming lessons, pending
   payments count, active students count — matches `GET /api/v1/dashboard/`.
3. Mark today's seeded lesson complete with a note.
4. Confirm the student's `lessons_remaining` decreased by 1 (roster view and
   `GET /api/v1/students/{id}/` agree).
5. Re-submit the same completion (retry) — confirm the count does NOT decrement again
   (`POST /api/v1/lessons/{id}/complete/` is idempotent).

## Validate User Story 2 — roster, student detail, payments (spec.md US2)

1. Open the roster — confirm each row shows package/remaining/payment status.
2. Open the low-package student — confirm the low-package flag is visible.
3. Register a manual payment (`POST /api/v1/payments/`) — confirm it appears in the
   payments list with the correct status.

## Validate User Story 3 — parent portal isolation (spec.md US3)

1. Log in (separate browser/session) as the seeded parent.
2. Confirm only their linked student's data is visible anywhere in the portal.
3. Attempt `GET /api/v1/students/{other_student_id}/` (a student NOT linked to this parent)
   directly against the API — confirm `404`, not the other student's data.
4. Confirm the lesson completed in US1, with its note, is visible read-only here.

## Validate User Story 4 — reminders (spec.md US4)

1. Confirm the seeded ~24h-out lesson has `reminder_sent_at` set after the Celery Beat sweep
   runs (check `celery-beat`/`celery-worker` logs, or query the Lesson via Django admin/API).
2. Confirm exactly one reminder is logged/sent for it (idempotency — running the sweep twice
   doesn't double-send).
3. Cancel a different seeded lesson before its reminder window and confirm no reminder fires
   for it.

## API documentation check

- `GET /api/docs/` renders Swagger UI from the drf-spectacular schema with all endpoints in
  `contracts/api.md` present.

## Automated test suites (what CI/local `test` commands should run)

```bash
docker compose exec backend pytest        # models, permission boundaries, package decrement, payment transitions
docker compose exec frontend npm test     # component/flow tests
```
