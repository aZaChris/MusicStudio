# Implementation Plan: Production Readiness (Phase 4)

**Branch**: `refactor/production-standards` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-production-readiness/spec.md`

## Summary

Make the API safe and operable in production. Code changes: refresh-token revocation with
simplejwt's blacklist app (logout endpoint, revoke-all command/admin action, daily purge,
15-minute access tokens); request-id middleware + JSON logs propagated to Celery; Sentry
with PII scrubbing; a proxy-aware client-IP helper and a Stripe webhook allowlist. Ops
changes: an `offsite` rclone-crypt sidecar in the Coolify compose, a restore-drill script
executed on a real dump, a Locust load test with a committed baseline, `check --deploy` in
CI, an Italian runbook. The OWASP walk is redone for all ten risks. Decisions in
[research.md](research.md); ADR-018…022.

## Technical Context

**Language/Version**: Python 3.12, Django 5.2 LTS, DRF 3.17

**Primary Dependencies**: existing stack + `sentry-sdk[django,celery]` (runtime),
simplejwt's bundled `token_blacklist` app (no new package), `locust` (uv group `load`
only), `rclone` image for the sidecar. No JSON-logging or IP library: stdlib.

**Storage**: PostgreSQL 16 (+2 simplejwt tables); S3-compatible bucket (non-AWS) for
encrypted off-site dumps.

**Testing**: pytest + pytest-django + factory_boy on real PostgreSQL; shell script checked
by running it on a real dump.

**Target Platform**: Linux containers on Coolify (Docker Compose build pack). Dev machine
has no Docker: local verification uses uv + local PostgreSQL/Redis + gunicorn.

**Project Type**: web service (REST API), modular monolith.

**Performance Goals**: 50 concurrent users, p95 < 500 ms on main reads, < 1% errors.

**Constraints**: no AWS; Stripe test mode only; no request-path DB read added for auth
(access tokens not blacklist-checked); Sentry free tier (sampling, traces default 0);
RPO ≤ 24 h, restore < 30 min.

**Scale/Scope**: 1–10 teachers per studio; load seed 10 studios / 50 teachers / 1500
students / ~1 year of lessons.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [X] I. Tenant data untouched; new logout endpoint gets a cross-user test (token of user B
  refused for user A); webhook unchanged in scoping.
- [X] II. Logout under `/api/v1/auth/`; `openapi.yaml` regenerated; `X-Request-ID` documented.
- [X] III. Tests with every change (logout, revoke, purge, request id, JSON formatter,
  scrubber, client_ip, allowlist); existing query budgets must not grow (blacklist check
  only on refresh).
- [X] IV. Exactly the phase 4 scope of the roadmap; phase 5 items stay out.
- [X] V. `apps/accounts/services.py` (logout, revoke_all_sessions), `apps/common/logging.py`,
  `apps/common/net.py`; views thin; mypy strict.
- [X] VI. No client code touched (frontend must handle 15-minute access tokens via refresh,
  which it already does by design of rotation).
- [X] VII. CI gains `check --deploy`; everything else unchanged and green.
- [X] VIII. ADR-018 revoca token, ADR-019 osservabilità, ADR-020 backup off-site,
  ADR-021 allowlist e IP reale, ADR-022 load test. Concepts: `revoca-token-jwt`,
  `log-strutturati-e-sentry`, `backup-off-site-e-restore-drill`, `load-testing`,
  `ip-reale-dietro-proxy`; runbook; glossary, Q&A, index, overview updated.
- [X] IX. Full OWASP walk; Sentry scrubbing and log redaction reviewed as data exposure.

Post-design re-check: still passing; no violations, Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-production-readiness/
├── plan.md  research.md  data-model.md  quickstart.md
├── contracts/api-changes.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/accounts/      services.py (logout, revoke_all_sessions), views.py (LogoutView),
│                       urls.py, admin.py (action), tasks.py (purge), management/commands/
│                       revoke_sessions.py, tests/test_logout.py, test_revoke.py
├── apps/common/        logging.py (JSON formatter, RequestIdFilter, RequestIdMiddleware,
│                       Celery signal hooks), net.py (client_ip), sentry.py (before_send),
│                       management/commands/seed_loadtest.py, raise_test_error.py, tests/
├── apps/payments/      webhooks.py (allowlist check), tests/test_webhook_allowlist.py
├── config/settings/    base.py (blacklist app, JWT 15 min, middleware, LOGGING), prod.py
│                       (JSON logs, Sentry, TRUSTED_PROXY_COUNT), test.py
├── config/celery.py    beat: purge expired tokens
├── loadtest/locustfile.py
└── pyproject.toml      sentry-sdk; group `load` = locust
docker-compose.coolify.yml   new env vars, `offsite` service, manifest hook on backup
docker/offsite/              rclone entrypoint + healthcheck (if needed beyond the image)
scripts/restore-drill.sh
.github/workflows/ci.yml     + check --deploy
.env.example                 new variables documented
docs/operations/runbook.md, restore-drill.md
docs/loadtest/<date>/
docs/learning/adr/ADR-018…022, concetti/*, glossario, colloquio, 00-indice, panoramica,
docs/learning/concetti/sicurezza-api-owasp.md
```

**Structure Decision**: existing modular monolith; no new Django app. Accounts owns token
lifecycle, common owns cross-cutting logging/networking, payments owns its webhook guard.

## Implementation order

1. US1 token revocation (P1) — code, migration, tests, ADR-018.
2. US3 request id + JSON logs + Sentry (P2, but needed to observe US2) — ADR-019.
3. US2 deploy hardening: env vars, `check --deploy` in CI, runbook.
4. US6 client_ip + webhook allowlist — ADR-021.
5. US4 manifest hook, offsite sidecar, restore-drill script executed locally — ADR-020.
6. US5 seed + Locust + baseline — ADR-022.
7. US7 OWASP walk, study docs, end-of-phase checklist.

## Owner tasks (cannot be done by the agent)

Coolify deploy on the real server, Sentry DSN, bucket + rclone crypt passwords,
drill against the real bucket, GitHub branch protection (carried over).

## Complexity Tracking

No violations.
