# Data Model: Production Readiness (Phase 4)

Only US1 adds database tables; everything else is files, settings or external storage.

## OutstandingToken / BlacklistedToken (simplejwt `token_blacklist` app)
Third-party models, migrations shipped by simplejwt; no custom model.
- **OutstandingToken**: `user` (FK, nullable), `jti` (unique), `token`, `created_at`,
  `expires_at`. One row per refresh token issued (login and every rotation).
- **BlacklistedToken**: `token` (OneToOne → OutstandingToken), `blacklisted_at`.
- **Rules**: a refresh token is usable only if not blacklisted; rotation blacklists the old
  one; logout blacklists the given one only if `outstanding.user == request.user`;
  `revoke_all_sessions(user)` blacklists every non-expired outstanding token of that user.
- **Purge**: rows with `expires_at < now` are deleted daily (beat task).
- **Tenant**: tokens belong to a user, not to a studio; no tenant scoping needed. Logout of
  another user's token is refused (cross-user test instead of cross-tenant test).
- **Volume**: ≈ one row per login + one per refresh (every 15 min of active use); purge
  keeps it bounded by `REFRESH_TOKEN_LIFETIME` (14 days).

## Backup artefacts (outside the database)
- **Dump**: `/backups/{daily,weekly,monthly}/musicstudio-<date>.sql.gz` (existing sidecar).
- **Expected row counts**: read from the dump's own COPY blocks at restore time (no
  manifest file; the dump is the snapshot).
- **Off-site copy**: same tree, encrypted by rclone crypt in the bucket.

## Restore drill record (`docs/operations/restore-drill.md`)
Date · dump used · source (local/off-site) · PostgreSQL version · duration · row-count
comparison · outcome · notes.

## Load-test baseline (`docs/loadtest/<date>/`)
`stats.csv`, `failures.csv`, `README.md` (machine, settings, users, spawn rate, duration,
per-endpoint rps/p50/p95/error rate, verdict against SC-005).
