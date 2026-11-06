> **Historical note (2026-11-06):** this document describes feature 001 as built. The AWS deployment target was replaced by Coolify (self-hosted) in feature 002 — see `specs/002-production-foundations/` and `docs/learning/adr/ADR-003-coolify-al-posto-di-aws.md`. AWS references below are kept only as history.

# Phase 0 Research: MusicStudio MVP

No `NEEDS CLARIFICATION` markers remained in the Technical Context — this consolidates the
concrete decisions behind it.

## Auth & multi-role access

- **Decision**: `User` extends Django's `AbstractUser` with a `role` field
  (`teacher | studio_owner | parent`), auth via `djangorestframework-simplejwt`
  (access + refresh tokens). `studio_owner` is modeled as a `Teacher` row with
  `is_owner=True` rather than a fourth entity — an owner IS a teacher who can also see their
  studio's other teachers.
- **Rationale**: keeps the role surface small (3 roles, matches spec) and avoids a parallel
  "owner" data model that duplicates Teacher fields.
- **Alternatives considered**: separate `StudioOwner` model — rejected, adds a join for no
  behavioral gain since an owner always has their own teaching practice too in this domain.

## Tenant isolation enforcement

- **Decision**: every ViewSet touching Student/Lesson/Package/Payment overrides
  `get_queryset()` to filter by `request.user`'s role (teacher → own students only;
  studio_owner → all students of teachers in their Studio; parent → only students linked via
  `ParentAccount`), backed by custom DRF permission classes (`IsTeacherOwner`,
  `IsParentOfStudent`) applied at the object level too (`has_object_permission`) so a guessed
  ID in a URL still 404s/403s.
- **Rationale**: Constitution Principle I requires ORM-level filtering, not serializer-level
  hiding — this is the standard DRF pattern for it (`get_queryset` + `IsOwnerOrReadOnly`-style
  permission classes), no third-party package needed.
- **Alternatives considered**: django-guardian (object-level permissions library) — rejected,
  overkill for 3 static roles with simple ownership rules; would add a dependency and a
  permission-table migration for something 4 `get_queryset()` overrides handle directly.

## Package decrement correctness

- **Decision**: decrement happens inside a single `Lesson.mark_completed()` model method
  wrapped in `transaction.atomic()` with `select_for_update()` on the Package row, guarded by
  checking `Lesson.status != Lesson.Status.COMPLETED` before decrementing (idempotent — calling
  it twice is a no-op the second time) and `Package.lessons_remaining > 0` (clamped, never
  negative — see spec edge cases).
- **Rationale**: this is the money-critical path (Constitution Principle III); doing it as one
  guarded, locked model method — not duplicated in the serializer and the viewset — is the
  smallest surface that can't be raced or double-decremented.
- **Alternatives considered**: Celery task for the decrement — rejected, this must be
  synchronous and immediately consistent for the teacher's next screen render; no reason to
  make it async.

## Background reminders

- **Decision**: Celery Beat runs a periodic task (every 15 min) that queries `Lesson`s with
  `status=SCHEDULED` and `start_time` between now+23h45m and now+24h, sends the parent
  reminder, and stamps a `reminder_sent_at` timestamp on the Lesson to make the job idempotent
  (re-running the same window twice never double-sends). A separate signal/check after
  `mark_completed()` evaluates `lessons_remaining <= 2` and surfaces the warning via a computed
  field the dashboard reads (no separate notification row needed for the teacher-facing
  warning — it's a read-time flag, not a sent message).
- **Rationale**: matches the spec's "demonstrably queued/sent" success criterion with a simple,
  inspectable poll rather than scheduling a one-off task per lesson (which would need
  rescheduling on every reschedule/cancel).
- **Alternatives considered**: `celery beat` one-shot ETA task scheduled at lesson-creation
  time — rejected, requires revoking/rescheduling on every lesson edit; a periodic sweep is
  simpler and self-healing if Celery was briefly down.
- **Email transport for MVP**: Django's console/file email backend in dev, SMTP (env-configured,
  e.g. any SMTP provider) in prod — no dedicated transactional-email service integration
  required for MVP; the requirement is "demonstrably queued/sent," not deliverability at scale.

## Frontend state & i18n

- **Decision**: TanStack Query for all server state (lists, mutations, cache invalidation on
  lesson-complete/payment-register); no separate global state library needed for MVP.
  `react-i18next` with two static resource bundles (`en.json`, `it.json`); language preference
  persisted in `localStorage`, default to browser locale via `i18next-browser-languagedetector`.
- **Rationale**: the app is CRUD-over-REST with no complex client-only state; adding Redux/
  Zustand on top of TanStack Query would duplicate cache TanStack already owns.
- **Alternatives considered**: Redux Toolkit — rejected as unnecessary weight for this scope.

## Theming

- **Decision**: CSS custom properties defined on `:root` (light) and overridden under
  `:root[data-theme="dark"]`, values derived from `design/tokens.md` (OKLCH palette, flipped
  lightness for dark). A small `ThemeProvider` toggles the `data-theme` attribute and persists
  choice in `localStorage`.
- **Rationale**: matches the design artboards' token system directly, zero runtime CSS-in-JS
  cost.
- **Alternatives considered**: Tailwind — viable but not needed; the design is a small, fixed
  token set better expressed as plain custom properties than a utility framework for this
  scope.

## Local dev & AWS deployment

- **Decision**: Docker Compose services: `db` (postgres:16), `redis`, `backend` (Django +
  gunicorn in prod image / runserver in dev), `celery-worker`, `celery-beat`, `frontend` (vite
  dev server locally; static build served via nginx or the backend's static files in prod).
  AWS target: ECS Fargate, one task definition per service sharing an `.env`-derived task
  role, RDS Postgres, ElastiCache Redis; documented as the primary path with a plain
  EC2 + `docker compose up` fallback documented in `infra/aws/README.md` for a lower-cost demo
  deployment.
- **Rationale**: matches the brief's explicit deliverable ("containerized deployment... is part
  of the deliverable, not an afterthought") while keeping local dev on the same images that
  ship to AWS.
- **Alternatives considered**: Elastic Beanstalk — rejected, ECS Fargate is more directly
  portfolio-relevant (explicit container orchestration) and maps 1:1 to the Compose services.

## API documentation

- **Decision**: `drf-spectacular` generating an OpenAPI 3 schema served at `/api/schema/` with
  Swagger UI at `/api/docs/`.
- **Rationale**: explicitly requested in the brief as a portfolio-relevant deliverable; it's
  the standard DRF-ecosystem choice (actively maintained, decorator-light for straightforward
  ViewSets).
