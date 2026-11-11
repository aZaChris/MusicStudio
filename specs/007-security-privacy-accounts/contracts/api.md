# API Contract: Security, Privacy and Accounts (Phase 007)

All under `/api/v1/`. The machine-readable contract is `backend/openapi.yaml`, regenerated in
the same change. Errors use the existing envelope (`apps/common/exceptions.py`).
"Uniform 202" means: same status and body whatever the input address.

## Auth (anonymous, rate limited per client)

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `auth/register/` | `first_name, last_name, email, password, studio_name, accept_terms` | uniform 202 `{"detail": "check_email"}`; 400 on invalid password/fields |
| POST | `auth/confirm-email/` | `uid, token` | 200 `{"detail": "confirmed"}`; 400 `invalid_or_expired` |
| POST | `auth/confirm-email/resend/` | `email` | uniform 202 |
| POST | `auth/password-reset/` | `email` | uniform 202 |
| POST | `auth/password-reset/confirm/` | `uid, token, new_password` | 200; 400 `invalid_or_expired` or password errors |
| POST | `auth/token/` (changed) | `email, password` | 200 `{access, refresh}` or 200 `{mfa_required: true, mfa_token}`; 401 generic `invalid_credentials` (wrong, unknown, locked, unconfirmed share the body; unconfirmed adds `code: email_not_confirmed` only after a correct password) |
| POST | `auth/mfa/verify/` | `mfa_token, code` (TOTP or recovery) | 200 `{access, refresh}`; 401 |
| GET | `invitations/lookup/?token=` | — | 200 `{role, studio_name, email, existing_account}`; 404 if invalid/expired/used |
| POST | `invitations/accept/` | `token, password?, first_name?, last_name?, accept_terms, consent?` | 201 `{access, refresh}`; existing account: must be signed in as that email, no password |

## Account (authenticated)

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `auth/password/change/` | `current_password, new_password` | 200; other sessions revoked |
| GET | `auth/mfa/` | — | `{enabled, recovery_codes_left}` (owner/teacher) |
| POST | `auth/mfa/setup/` | — | 201 `{secret, otpauth_uri}` (unconfirmed device) |
| POST | `auth/mfa/confirm/` | `code` | 200 `{recovery_codes: [10]}` shown once |
| POST | `auth/mfa/disable/` | `password, code` | 204 |
| POST | `auth/mfa/recovery-codes/` | `password, code` | 200 new codes, old ones invalid |
| GET | `me/` (changed) | — | adds `email_verified`, `mfa_enabled`, role `student` |

## Invitations (owner: all roles in studio; teacher: parent/student for own students)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `invitations/` | — | scoped list `{id, email, role, students, status, expires_at}` |
| POST | `invitations/` | `email, role, student_ids?` | 201; 400 if role not allowed, student minor for `student`, or out-of-scope id (as "does not exist") |
| POST | `invitations/{id}/revoke/` | — | 200; 404 out of scope |

## Students (changed)

- `students/` read/write gains `is_adult` (bool) and read-only `has_account`.
- Student role: `GET students/` returns only their own record; lessons, packages, payments
  likewise; every write 403.

## Privacy (parent, adult student)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `privacy/consents/` | — | own consent records |
| POST | `privacy/consents/{id}/withdraw/` | `password` | 202; erasure of affected children starts |
| GET | `privacy/export/` | — | 200 JSON attachment (`Content-Disposition`) with account, children, lessons, packages, payments, consents |
| POST | `privacy/erase/` | `password` | 202; 409 `checkout_open` while an online payment is pending; owner: 409 `studio_not_empty` |

## Audit (owner)

| Method | Path | Query | Response |
|---|---|---|---|
| GET | `audit/` | `action`, `since`, `until`, `page` | paginated entries of own studio, newest first; 403 other roles |

## Operator (management commands, audited)

- `manage.py unlock_account <email>`
- `manage.py reset_mfa <email>`
- `manage.py rotate_field_keys`
- `manage.py run_retention` (also scheduled daily in Celery beat)
