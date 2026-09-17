# MusicStudio

A web platform for private music teachers and small studios (1-10 teachers) to manage
students, recurring lessons, lesson packages, payments, and parent communication —
replacing a patchwork of Calendly + spreadsheets + WhatsApp.

Built spec-first with [spec-kit](https://github.com/github/spec-kit); the full spec, plan,
research, data model, API contracts, and task breakdown live in
[`specs/001-musicstudio-mvp/`](specs/001-musicstudio-mvp/).

## Stack

- **Backend**: Django 5 + Django REST Framework (API-only), PostgreSQL, JWT auth
  (`djangorestframework-simplejwt`), Celery + Redis for background reminders,
  `drf-spectacular` for OpenAPI docs.
- **Frontend**: React 19 + Vite + TypeScript SPA, TanStack Query, `react-i18next`
  (English/Italian), CSS-custom-property light/dark theming.
- **Infra**: Docker Compose for local dev; AWS (ECS Fargate primary, EC2 + Compose
  fallback) for deployment — see [`infra/aws/README.md`](infra/aws/README.md).

## Repository layout

```text
backend/    Django project (apps/accounts, studios, students, packages, lessons,
            payments, notifications, common)
frontend/   React SPA (src/features/{teacher,parent}, auth, theme, i18n, api)
infra/      docker-compose.yml, Dockerfiles, .env.example, AWS deployment docs
design/     Reference design artboards + extracted design tokens
specs/      spec-kit artifacts: spec, plan, research, data model, contracts, tasks
```

Two long-lived branches: `web` (this Django/DRF + React platform) and a future `app`
branch (React Native, same API — out of scope for this MVP, see the constitution).

## Local development

```bash
cd infra
cp .env.example .env   # fill in real values (see comments in the file)
docker compose up --build
```

This starts Postgres, Redis, the Django API (`:8000`), Celery worker + beat, and the
Vite dev server (`:5173`). First run:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo   # optional demo data + logins
```

Full validation walkthrough (what to click through, what each user story should do):
[`specs/001-musicstudio-mvp/quickstart.md`](specs/001-musicstudio-mvp/quickstart.md).

API docs once the backend is running: `http://localhost:8000/api/docs/`.

### Running without Docker (backend)

```bash
cd backend
uv sync
DATABASE_URL=sqlite:///dev.sqlite3 DJANGO_SECRET_KEY=dev uv run python manage.py migrate
DATABASE_URL=sqlite:///dev.sqlite3 DJANGO_SECRET_KEY=dev uv run python manage.py runserver
```

### Tests

```bash
cd backend && uv run pytest apps      # backend: models, permission boundaries, business logic
cd frontend && npm test               # frontend: component/flow tests
```

## Architecture notes

- **Tenant isolation is enforced at the ORM layer**, not just hidden in the UI: every
  viewset scopes its queryset by role through
  `backend/apps/common/permissions.py::role_scoped_queryset` — a parent account cannot
  retrieve another family's data through the API, full stop. See the project
  [constitution](.specify/memory/constitution.md), Principle I.
- **API-first**: the Django backend has no server-rendered app views; the React SPA is
  one client of a REST API a future React Native app can reuse unchanged.
- Package lesson-count decrement, payment status transitions, and every permission
  boundary have explicit automated test coverage (Constitution Principle III).
