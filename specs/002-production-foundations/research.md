# Research: Production Foundations (Phase 1)

Each entry: Decision / Rationale / Alternatives considered. The Italian ADRs in
`docs/learning/adr/` expand the architectural ones.

## Starting point
- **Decision**: branch from `4be062d` (last Django commit). ADR-001.
- **Rationale**: only commit with the required stack; 26 green tests.
- **Alternatives**: base on `app` and restore `backend/` (mixes Expo at repo root); rewrite
  from `web` (forbidden "start from scratch").

## Service layer shape
- **Decision**: per-app `services.py` (writes, plain functions, keyword args, transactional)
  and `selectors.py` (reads returning querysets). ADR-002.
- **Rationale**: the HackSoft Django styleguide pattern; minimal ceremony, testable without
  HTTP, keeps Django's ORM visible.
- **Alternatives**: repository pattern over the ORM (hides the ORM, duplicates it); fat
  models (rules scattered across save()/properties; hidden queries); DDD aggregates (too heavy
  for this size).

## Scoping writes
- **Decision**: serializer mixin that replaces related-field querysets with the user's
  visible set at instantiation.
- **Rationale**: DRF validates PKs against the field queryset, so an out-of-scope id becomes
  a normal 400 "invalid pk" — no existence leak, one place to maintain.
- **Alternatives**: checks in each `perform_create` (easy to forget on update); object-level
  permissions on related objects (DRF does not apply them to related fields).

## N+1 removal
- **Decision**: `Prefetch(..., to_attr="active_packages")` for the active package object,
  `Subquery` annotation for the latest payment status, annotated `Count` for teacher_count,
  one annotated query for low-package students.
- **Rationale**: constant query count; keeps response shape identical.
- **Alternatives**: denormalised columns (write complexity, stale data); caching (hides the
  problem, phase 3 topic).

## Django version
- **Decision**: Django 5.2 LTS.
- **Rationale**: 5.1 is out of security support since Dec 2025; 5.2 LTS supported to Apr 2028;
  no breaking change affects this codebase (verified by the test suite).
- **Alternatives**: Django 6.0 (newer, but not LTS; shorter support window).

## Settings
- **Decision**: `base/dev/test/prod` modules, django-environ, prod uses `env()` without
  defaults for secrets so start-up fails fast. ADR-004.
- **Alternatives**: single settings file with if-branches (hard to read); pydantic-settings
  (extra dependency for no gain here).

## Health endpoints
- **Decision**: `/health/live/` (no I/O) and `/health/ready/` (DB `SELECT 1` + Redis
  `PING`, 503 on failure), unauthenticated, not throttled, exempt from HTTPS redirect. ADR-006.
- **Alternatives**: django-health-check package (more than needed); a single endpoint
  (a DB blip would make Docker restart healthy web containers).

## Rate limiting
- **Decision**: DRF throttles backed by the Django cache (Redis): `login` 5/min,
  `anon` 100/hour, `user` 1000/hour, configurable by env.
- **Alternatives**: django-axes (account lockout, enables DoS on known emails); proxy-level
  limiting in Coolify/Traefik (not portable, not testable in CI) — can be added on top later.

## Static files
- **Decision**: whitenoise serves `/static/` (admin, DRF browsable API, Swagger assets).
- **Alternatives**: separate nginx container (another service to operate for a few files).

## Reminder sweep concurrency
- **Decision**: claim each lesson with `UPDATE … SET reminder_sent_at=now WHERE id=… AND
  reminder_sent_at IS NULL`; send only if 1 row updated (at-most-once). ADR-008.
- **Alternatives**: send then mark (current; duplicates on overlap/crash); `select_for_update
  (skip_locked)` over the whole batch inside one transaction (holds locks while sending email);
  outbox table with per-recipient status (correct at-least-once + dedup, phase 3).

## Deployment target
- **Decision**: Docker Compose on Coolify; root `docker-compose.coolify.yml`; services
  routed by Coolify's proxy via domain set in the UI or `SERVICE_URL_BACKEND_8000`; no
  `ports:`; required vars `${VAR:?}`. ADR-003.
- **Rationale**: Coolify docs: "A published host port bypasses domain-based proxy routing";
  `${VAR:?}` "prevents deployment until a value is entered".
- **Alternatives**: AWS ECS (forbidden by guidelines, costly for this scale); Kubernetes
  (operational overkill); Coolify's Dockerfile build pack (cannot express worker/beat/backup).

## Backups
- **Decision**: `prodrigestivill/postgres-backup-local:16` sidecar, `@daily`, keep 7 days /
  4 weeks / 6 months, volume `db-backups`, built-in healthcheck. ADR-005.
- **Alternatives**: Coolify's built-in scheduled backups (only for databases created as
  separate Coolify resources, not for a db inside our Compose file); cron on the host (not
  versioned with the app); WAL archiving / PITR (phase 4 if needed).

## Healthchecks for workers
- **Decision**: worker `celery inspect ping` against its own node; beat: freshness of its
  schedule file (stdlib script); db `pg_isready`; redis `redis-cli ping`; backup image's own
  check.
- **Alternatives**: no healthcheck for beat (violates the constitution); beat as
  `worker -B` (single point, not recommended for production).

## CI
- **Decision**: one GitHub Actions job with Postgres 16 and Redis 7 services; `uv sync
  --frozen`; ruff check, ruff format --check, mypy, `makemigrations --check`, pytest with
  `--cov-fail-under=90`. ADR-007.
- **Alternatives**: separate jobs per tool (slower, duplicated setup for a small project);
  tox/nox (another layer for one Python version).
