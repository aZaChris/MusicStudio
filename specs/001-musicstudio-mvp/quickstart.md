# Quickstart: validate MusicStudio end-to-end

Two ways to run the stack, and what each one proves:

| Track | Compose file | Use it to check |
|---|---|---|
| **A. Local** | `docker-compose.yml` | the whole product with demo data: user stories US1–US4 |
| **B. Coolify (staging)** | `docker-compose.coolify.yml` | the production image and settings: build, start-up order, health checks, Celery Beat, real SMTP |

Track B never uses `seed_demo`: its accounts share the password `password123` and a staging
server is public. Staging is checked with a real sign-up instead.

> **Status (2026-11-13)**: migrations, `seed_demo`, the API walk for US1–US3 and the reminder
> logic (US4, run twice: one email, no duplicate, a cancelled lesson gets none) have been
> verified against a real PostgreSQL without Docker. Track A and B as written below have not
> been run end to end yet; T055 in `tasks.md` stays open until they are.

## Track A: local stack

Prerequisites: Docker with Compose v2 (in WSL, enable the Docker Desktop integration).

```bash
cp .env.example .env          # defaults work for a local run; the console email backend is fine
docker compose --profile frontend up --build
```

This starts `db` (PostgreSQL 16), `redis`, `backend` (Django, port 8000), `worker`, `beat` and,
because of the `frontend` profile, the Vite dev server on port 5173. The backend applies the
migrations by itself at start-up.

Wait until `docker compose ps` shows every service as `healthy`, then:

```bash
curl -s localhost:8000/health/ready/                          # 200: database and Redis are reachable
docker compose exec backend python manage.py seed_demo        # demo data
```

`seed_demo` creates a solo teacher (`solo.teacher@example.com`), a studio owner
(`owner@example.com`) with a second teacher (`teacher2@example.com`), students with active
packages (one with a single lesson left), a parent (`parent@example.com`) linked to that
student, and a lesson about 24 hours from now. The password for all of them is `password123`.

### US1: the teacher's week and completing a lesson

1. Open `http://localhost:5173` and log in as the teacher.
2. The dashboard shows the week, the next lessons, the pending payments and the active
   students; the numbers match `GET /api/v1/dashboard/`.
3. Complete today's lesson with a note.
4. The student's remaining lessons drop by 1 (roster and student page agree).
5. Send the same completion again (a retry): the count must not drop twice.

### US2: roster, student page, payments

1. The roster shows package, remaining lessons and payment status for each student.
2. The student with one lesson left shows the low-package warning.
3. Register a manual payment: it appears in the payments list with the right status.

### US3: the parent portal

1. In a separate browser session, log in as `parent@example.com`.
2. Only the linked student is visible anywhere.
3. `GET /api/v1/students/{id}/` for a student who is not linked answers `404`, not the data.
4. The lesson completed in US1, with its note, is visible read-only.

### US4: reminders

The sweep runs every 15 minutes and looks at lessons starting 23h45 to 24h from now. The seeded
lesson sits right at the edge, so to avoid waiting up to 15 minutes, move it into the window:

```bash
docker compose exec backend python manage.py shell -c "
import datetime
from django.utils import timezone
from apps.lessons.models import Lesson
l = Lesson.objects.filter(status='scheduled', reminder_sent_at__isnull=True).order_by('-start_time').first()
l.start_time = timezone.now() + datetime.timedelta(hours=23, minutes=52); l.save()
print(l.pk, l.start_time)"
```

1. Within 15 minutes the `beat` log shows the task being sent and the `worker` log shows it
   running. This is the one thing only Docker proves: the scheduler fires by itself.
2. The lesson now has `reminder_sent_at` set, and one email for the parent is printed in the
   `worker` log (console backend).
3. The sweep runs again 15 minutes later: no second email (it is idempotent).
4. Cancel another scheduled lesson before its window: no reminder appears for it.

### API documentation

`http://localhost:8000/api/docs/` shows Swagger UI with the endpoints of `contracts/api.md`.

## Track B: Coolify staging

Prerequisites: the project already exists in Coolify with its variables (the required ones,
marked `:?` in `docker-compose.coolify.yml`, are `SMTP_*`, `DEFAULT_FROM_EMAIL` and
`FIELD_ENCRYPTION_KEYS`). Use Stripe in test mode only.

1. Deploy and wait. The deploy is good only when all six services are `healthy`: `db`, `redis`,
   `backend`, `worker`, `beat` and `web` (the SPA behind nginx). The backend check is
   `/health/ready/`, so a healthy backend already means PostgreSQL and Redis answer.
2. Open the public URL: the landing loads and the video poster appears.
3. Sign up as a teacher at `/register`, confirm the email (a real message through the SMTP
   provider), log in.
4. Create a student, invite a parent with an email address you control, and accept the
   invitation in another browser session. The parent sees only that student.
5. Schedule a lesson for that student starting in 23h50 from now.
6. Check US4 as in track A: the `beat` log shows the sweep, the parent receives a real email
   within 15 minutes, and a second sweep sends nothing.
7. `/health/ready/` answers 200; stop `redis` for a minute and it must answer 503 (and the API
   itself keeps working: throttles fail open); start it again and it returns to 200.

## Automated test suites

```bash
cd backend && uv run pytest                  # coverage floor 90%
cd frontend && npm test                      # Vitest, capped at 2 workers
```

CI runs both, plus lint, types, the OpenAPI check and the portal image build.
