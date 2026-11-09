# Research: Production Readiness (Phase 4)

Sources: current code (`config/settings/*`, `docker-compose.coolify.yml`, `apps/payments/`,
`config/health.py`), simplejwt 5.5 docs (token_blacklist app), Sentry Python SDK docs,
rclone docs (crypt remote), Stripe "IP addresses" docs (`ips_webhooks.json`).
Constraint: Docker is not available on the dev machine (WSL), so everything verifiable
locally must run with uv + local PostgreSQL 16 + Redis.

## Token revocation (US1) — ADR-018
- **Decision**: enable simplejwt's `rest_framework_simplejwt.token_blacklist` app with
  `BLACKLIST_AFTER_ROTATION=True`. New `POST /api/v1/auth/logout/` blacklists the given
  refresh token after checking it belongs to `request.user`. "Revoke all sessions" is a
  service (`revoke_all_sessions(user)`) exposed as a management command and a Django admin
  action (operators only, no public endpoint). Expired rows purged daily by a beat task
  calling simplejwt's `flushexpiredtokens` logic.
- **Access token lifetime**: default lowered from 60 to 15 minutes (`JWT_ACCESS_MINUTES`
  still overrides). Access tokens are not checked against the blacklist: that would add a
  query to every request. 15 minutes bounds the window after logout.
- **Alternatives**: blacklist access tokens too (a DB/Redis read per request); server-side
  sessions (drops JWT, breaks existing clients); token version counter on the user (one
  query per request, revokes everything only, no per-device logout).

## Error tracking (US3) — ADR-019
- **Decision**: `sentry-sdk` with Django and Celery integrations, initialised in
  `config/settings/prod.py` only when `SENTRY_DSN` is set. `send_default_pii=False`, a
  `before_send` hook that drops `Authorization`, cookies, `Stripe-Signature` and request
  bodies of auth/webhook endpoints; tags `request_id` and `studio_id`.
  `traces_sample_rate` from env, default 0 (free tier quota).
- **Alternatives**: self-hosted GlitchTip (another service to run and back up); email on
  error via Django `AdminEmailHandler` (no grouping, leaks data into mailboxes).

## Structured logs and request id (US3) — ADR-019
- **Decision**: stdlib only. `apps/common/logging.py` holds a JSON formatter (~25 lines),
  a `RequestIdFilter` reading a `contextvars.ContextVar`, and a middleware that takes
  `X-Request-ID` from the proxy if it looks valid (≤ 64 chars, `[A-Za-z0-9-]`) or generates
  a UUID4, echoes it in the response, and writes one access line per request (method, route,
  status, duration_ms, request_id, user_id). Celery: `before_task_publish` copies the id
  into task headers, `task_prerun`/`task_postrun` set and reset it. `prod` uses the JSON
  formatter; `dev` keeps plain text.
- **Alternatives**: python-json-logger or structlog (a dependency for ~25 lines of code);
  gunicorn access log (no request id, no user, not JSON by default).

## Load testing (US5) — ADR-022
- **Decision**: Locust in a separate uv dependency group `load` (not installed in the image
  nor in CI). `backend/loadtest/locustfile.py` with weighted tasks on token, lessons,
  calendar, dashboard, packages. A `seed_loadtest` management command creates a realistic
  studio set (10 studios × 5 teachers × 30 students, a year of lessons) and refuses to run
  with `DEBUG=False` unless `--i-know-this-is-not-production`. Run headless against
  gunicorn with prod-like settings on the local machine; CSV + summary committed to
  `docs/loadtest/` with the machine description (results are hardware-dependent and say so).
- **Target**: 50 users, p95 < 500 ms, errors < 1% (SC-005); misses are documented, not hidden.
- **Alternatives**: k6 (JavaScript, another runtime); JMeter (heavy, XML); ab/wrk (no
  realistic flows with auth).

## Off-site backups and restore drill (US4) — ADR-020
- **Decision**: keep the `postgres-backup-local` sidecar (ADR-005) and add an `offsite`
  sidecar running `rclone` on a schedule: `rclone copy /backups offsite:` where `offsite`
  is an rclone **crypt** remote over any S3-compatible bucket (e.g. Backblaze B2,
  Cloudflare R2, Hetzner Object Storage; never AWS). Client-side encryption. `copy` never
  deletes remotely; `rclone delete --min-age` removes copies older than the longest local
  retention (6 months). Changed during implementation from `sync`: with `sync`, a wiped or
  compromised local volume would empty the bucket on the next run. On failure it pings
  an optional `BACKUP_ALERT_URL` (healthchecks.io-style dead-man switch) and the container
  healthcheck turns unhealthy when the last success is older than 26 h.
- **Restore drill**: `scripts/restore-drill.sh <dump-file|--from-remote>` restores into a
  brand-new database, checks migrations, compares the row count of every table with the
  rows contained in the dump itself (counted from its COPY blocks: the dump is the snapshot,
  so no separate manifest is needed), prints the elapsed time. Dumps are taken with
  `--no-owner --no-privileges` so they restore into any role. Executed locally without Docker
  (PostgreSQL 16) on a real dump; the record goes to `docs/operations/restore-drill.md`.
  Running it against the real bucket needs the owner's credentials: owner task.
- **Alternatives**: Coolify's built-in S3 backups (only for databases created as separate
  Coolify resources, ADR-005); `rclone sync` (mirrors local deletions, so a wiped
  volume empties the bucket); provider lifecycle rules (differ per provider, outside the
  repo); pgBackRest/WAL archiving (point-in-time recovery is
  more than a 1–10 teacher product needs today).

## Stripe webhook allowlist (US6) — ADR-021
- **Decision**: `STRIPE_WEBHOOK_ALLOWED_IPS` (comma list, from Stripe's published
  `ips_webhooks.json`); empty = check disabled (dev/tests). The client address is computed
  by `apps/common/net.py::client_ip(request)`: with `TRUSTED_PROXY_COUNT=N` it takes the N-th
  address from the right of `X-Forwarded-For` (the one appended by our proxy), else
  `REMOTE_ADDR`. Never the left-most value, which the caller controls. Refused → 403, logged,
  nothing stored, checked before signature verification.
- **Alternatives**: allowlist in Traefik/Coolify labels (outside the repo and its tests);
  trusting the left-most XFF (spoofable); `django-ipware` (dependency for one function).

## Deploy and runbook (US2)
- **Decision**: keep the existing Coolify compose; add the new env vars, the `offsite`
  service, and a `check_deploy` step: the web entrypoint already runs migrations; add
  `manage.py check --deploy --fail-level WARNING` to CI with prod settings and dummy env.
  Rollback = redeploy the previous commit in Coolify (images are rebuilt from git; migrations
  must stay backward compatible for one release, documented). Runbook in Italian at
  `docs/operations/runbook.md`: first deploy, secrets list, rollback, secret rotation
  (JWT key rotation logs everybody out, said explicitly), restore.
- **Owner tasks** (need accounts/servers the agent does not have): real Coolify deploy,
  Sentry project + DSN, bucket + rclone credentials, executing the drill on the real bucket.
- **Health (FR-006)**: `/health/ready/` already checks PostgreSQL and Redis (the broker);
  responses only say ok/error per check. No change beyond a test that no exception text
  leaks.

## OWASP walk (US7)
- Expected changes: API2 partial → covered (blacklist, logout, 15-minute access tokens);
  API10 gains the allowlist; API8 gains `check --deploy` in CI and Sentry scrubbing; API4
  gains load-test evidence. Each gap found during the walk gets a test or an explicit
  accepted-risk line.
