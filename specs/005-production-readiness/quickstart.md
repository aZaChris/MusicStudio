# Quickstart: validating Phase 4

Prereqs: `cd backend && uv sync`, PostgreSQL 16 and Redis running, `DATABASE_URL` set.

1. **Quality gate**: the commands in `CLAUDE.md` all green (ruff, mypy, migrations check,
   pytest ≥ 90%, spectacular `--fail-on-warn`), plus
   `uv run python manage.py check --deploy --settings=config.settings.prod` with dummy env.
2. **Logout (US1)**: obtain tokens → `POST /api/v1/auth/logout/` with the refresh → 205;
   `POST /api/v1/auth/token/refresh/` with the same refresh → 401. Covered by tests in
   `apps/accounts/tests/test_logout.py`.
3. **Revoke all**: `uv run python manage.py revoke_sessions teacher@example.com` → every
   refresh of that user → 401; another user's refresh still works.
4. **Logs (US3)**: run gunicorn with prod-like settings, make a request with
   `X-Request-ID: demo-123` → response echoes it; the access log line is JSON with
   `request_id=demo-123`; a Celery task enqueued by that request logs the same id.
5. **Sentry**: with a test DSN, run `manage.py raise_test_error` (raises inside a request-like context and a Celery task) → events visible
   within 1 minute, no `Authorization` header, no email. Without DSN the API still works.
6. **Allowlist (US6)**: tests send a signed event from an allowed and a non-allowed
   address, and with a forged left-most `X-Forwarded-For`: only the allowed one is stored.
7. **Restore drill (US4)**: `scripts/restore-drill.sh <dump>` → new database restored,
   row counts match the manifest, duration printed; record added to
   `docs/operations/restore-drill.md`.
8. **Load test (US5)**: `uv run --group load locust -f loadtest/locustfile.py --headless
   -u 50 -r 5 -t 5m --csv ...` against local gunicorn; results under `docs/loadtest/`.
9. **Owner-only**: deploy on Coolify following `docs/operations/runbook.md`, set
   `SENTRY_DSN` and rclone credentials, run the drill with `--from-remote`.
