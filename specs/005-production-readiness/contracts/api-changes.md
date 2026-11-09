# API Contract Changes: Production Readiness (Phase 4)

## POST /api/v1/auth/logout/  (new)
Auth: JWT access token. Throttle: user rate.
Request: `{"refresh": "<refresh token>"}`
- 205 Reset Content, empty body: token blacklisted (also when it was already blacklisted:
  idempotent, no state leak).
- 400 `{"refresh": [...]}`: missing/malformed/expired token, or a token that belongs to a
  different user (same message as malformed: no hint that the token is valid).
- 401 no/invalid access token.

## POST /api/v1/auth/token/refresh/  (behaviour change)
- A refresh token that was rotated or logged out → 401 `{"code": "token_not_valid"}`.
- Access token lifetime default 15 minutes (was 60).

## POST /api/v1/webhooks/stripe/  (behaviour change)
- 403 `{"detail": "Forbidden."}` when `STRIPE_WEBHOOK_ALLOWED_IPS` is set and the caller
  address is not in it. Checked before the signature; nothing stored.

## All endpoints
- Response header `X-Request-ID` (echoes a valid incoming one, else a new UUID).

## Operator interfaces (not HTTP)
- `manage.py revoke_sessions <email>`: blacklists all sessions of one account, prints count.
- Django admin action "Revoke all sessions" on users.
- `manage.py raise_test_error`: sends a test error to Sentry (no HTTP trigger, no attack surface).
- `manage.py seed_loadtest [--i-know-this-is-not-production]`.
- `scripts/restore-drill.sh <dump-file>` / `--from-remote <path>`.
