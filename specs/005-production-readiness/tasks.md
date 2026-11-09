# Tasks: Production Readiness (Phase 4)

**Input**: `specs/005-production-readiness/` · **Tests**: REQUIRED (constitution III) ·
**Docs/ADR**: REQUIRED (constitution VIII) · 👤 = needs the owner (accounts/servers)

## Phase 1: Setup

- [X] T001 Add `sentry-sdk[django,celery]` to runtime deps and a `load` dependency group with `locust` in `backend/pyproject.toml`; `uv lock`
- [X] T002 Document new variables (`JWT_ACCESS_MINUTES=15`, `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`, `TRUSTED_PROXY_COUNT`, `STRIPE_WEBHOOK_ALLOWED_IPS`, `RCLONE_*`, `BACKUP_ALERT_URL`) in `.env.example`

## Phase 2: Foundational

- [X] T003 `backend/apps/common/net.py::client_ip(request)` honouring `TRUSTED_PROXY_COUNT` (right-most trusted entry of `X-Forwarded-For`, else `REMOTE_ADDR`) + tests in `backend/apps/common/tests/test_net.py`

## Phase 3: US1 — Logout and revocation (P1) 🎯

- [X] T004 [US1] Enable `rest_framework_simplejwt.token_blacklist`, `BLACKLIST_AFTER_ROTATION`, access lifetime default 15 min in `backend/config/settings/base.py`; migrate
- [X] T005 [P] [US1] Tests: logout → refresh refused; logout twice harmless; token of another user → 400 and untouched; rotated refresh replay → 401; revoke-all affects only that user; purge removes only expired rows; in `backend/apps/accounts/tests/test_logout.py`
- [X] T006 [US1] `logout(user, refresh)` and `revoke_all_sessions(user)` in `backend/apps/accounts/services.py`; `LogoutView` + route `auth/logout/` in `backend/apps/accounts/views.py`, `urls.py`
- [X] T007 [US1] `revoke_sessions` command in `backend/apps/accounts/management/commands/revoke_sessions.py`; admin action in `backend/apps/accounts/admin.py`
- [X] T008 [US1] `purge_expired_tokens` task in `backend/apps/accounts/tasks.py` + daily beat entry in `backend/config/celery.py`
- [X] T009 [US1] Regenerate `backend/openapi.yaml`; ADR-018 in `docs/learning/adr/ADR-018-revoca-dei-token.md`

## Phase 4: US3 — Request id, JSON logs, Sentry (P2, needed by US2)

- [X] T010 [P] [US3] Tests: id echoed / generated / invalid replaced; access line JSON with route, status, duration, request_id; Celery task inherits id; formatter outputs valid JSON with exception; scrubber drops Authorization, cookies, Stripe-Signature, emails; in `backend/apps/common/tests/test_logging.py`, `test_sentry.py`
- [X] T011 [US3] `backend/apps/common/logging.py` (contextvar, `RequestIdMiddleware`, `RequestIdFilter`, `JsonFormatter`, Celery signal hooks connected in `apps.py`)
- [X] T012 [US3] `backend/apps/common/sentry.py` (`init_sentry()`, `before_send`) called from `backend/config/settings/prod.py` only when `SENTRY_DSN` set; JSON `LOGGING` in prod, middleware in base
- [X] T013 [US3] `raise_test_error` command in `backend/apps/common/management/commands/raise_test_error.py`
- [X] T014 [US3] ADR-019 in `docs/learning/adr/ADR-019-osservabilita-log-e-sentry.md`

## Phase 5: US2 — Deploy hardening and runbook (P1)

- [X] T015 [US2] New env vars on backend/worker/beat in `docker-compose.coolify.yml`; `TRUSTED_PROXY_COUNT=1` default in prod
- [X] T016 [US2] `manage.py check --deploy` with prod settings and dummy env in `.github/workflows/ci.yml`; fix any warning it raises; test that `/health/ready/` never returns exception text in `backend/apps/common/tests/` (or existing health tests)
- [X] T017 [US2] Italian runbook `docs/operations/runbook.md`: first deploy, secrets, rollback, secret rotation, restore, owner checklist
- [ ] T018 [US2] 👤 Deploy on Coolify following the runbook; verify HTTPS + `/health/ready/` + rollback time

## Phase 6: US6 — Stripe webhook allowlist (P3)

- [ ] T019 [P] [US6] Tests: allowed IP processed; other IP 403 and nothing stored; forged left-most XFF refused; empty setting disables check but signature still required; in `backend/apps/payments/tests/test_webhook_allowlist.py`
- [ ] T020 [US6] `STRIPE_WEBHOOK_ALLOWED_IPS` setting + check in `backend/apps/payments/webhooks.py`; ADR-021 `docs/learning/adr/ADR-021-allowlist-webhook-e-ip-reale.md`

## Phase 7: US4 — Off-site backups and restore drill (P2)

- [ ] T021 [US4] Row-count manifest written next to each dump (backup hook script) and `offsite` rclone-crypt service with healthcheck/alert in `docker-compose.coolify.yml` + `docker/offsite/`
- [ ] T022 [US4] `scripts/restore-drill.sh` (dump or `--from-remote`, fresh DB, migrate check, row counts vs manifest, elapsed time)
- [ ] T023 [US4] Execute the drill locally on a real dump of a seeded database; record in `docs/operations/restore-drill.md`; ADR-020 `docs/learning/adr/ADR-020-backup-off-site.md`
- [ ] T024 [US4] 👤 Create bucket + rclone crypt credentials in Coolify; run the drill with `--from-remote`

## Phase 8: US5 — Load test (P3)

- [ ] T025 [P] [US5] `seed_loadtest` command + test (refuses with `DEBUG=False` without flag) in `backend/apps/common/management/commands/seed_loadtest.py`
- [ ] T026 [US5] `backend/loadtest/locustfile.py` (token, lessons, calendar, dashboard, packages)
- [ ] T027 [US5] Run 50 users against local gunicorn with prod-like settings; commit results in `docs/loadtest/2026-11-09/`; document misses; ADR-022 `docs/learning/adr/ADR-022-load-test-con-locust.md`

## Phase 9: US7 — OWASP walk and study docs (P2)

- [ ] T028 [US7] Full OWASP API Top 10 walk in `docs/learning/concetti/sicurezza-api-owasp.md` (verdict + evidence ×10, gaps fixed with tests)
- [ ] T029 [P] [US7] Concept docs (800–1500 words): `revoca-token-jwt.md`, `log-strutturati-e-sentry.md`, `backup-off-site-e-restore-drill.md`, `load-testing.md`, `ip-reale-dietro-proxy.md` in `docs/learning/concetti/`
- [ ] T030 [US7] Glossary, interview Q&A, overview, `00-indice.md` (reading order + "Riepilogo della fase 4"); KB entries for non-trivial problems in `docs/knowledge-base/`

## Phase 10: Polish

- [ ] T031 Full quality gate green; tasks marked; CLAUDE.md status
- [ ] T032 Add "Fase 4 - Produzione" to `scripts/export-study-docs.sh` and run it; vault decisions; phase summary commit

## Dependencies

T001–T003 first. US1 independent. US3 before US2 (logs needed to verify deploy). US6
depends on T003. US4 and US5 independent of code stories. US7 last. 👤 tasks (T018, T024)
do not block closing the code work; they stay open and are listed in the summary.

## Parallel opportunities

Test tasks marked [P] (T005, T010, T019, T025) can be written alongside their stories;
concept docs (T029) in parallel with each other.

## Implementation strategy

MVP = US1 (closes OWASP API2). Then observability, deploy config, allowlist, backups, load
test, docs. Commit after each story.
