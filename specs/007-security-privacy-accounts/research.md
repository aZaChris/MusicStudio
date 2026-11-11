# Research: Security, Privacy and Accounts (Phase 007)

Each entry: Decision / Rationale / Alternatives considered. ADR numbers continue from ADR-026.

## R1. Email confirmation and password reset tokens

- **Decision**: no token table. Reset uses Django's `PasswordResetTokenGenerator` (HMAC over
  user id, password hash, last login and timestamp; `PASSWORD_RESET_TIMEOUT = 3600`). Email
  confirmation uses `django.core.signing.dumps` with its own salt over
  `(user_id, email, email_verified)`, checked with `max_age=48h`. Both links carry
  `uid` + `token` and are verified by the backend; the SPA only forwards them.
- **Rationale**: single-use comes for free: the reset token stops working once the password
  hash changes (and every newer reset changes it again); the confirmation token stops working
  once `email_verified` flips. Nothing to store, purge or leak from the database.
- **Alternatives**: a `OneTimeToken` table with hashed tokens (more code, needs purging, same
  guarantees); JWT-based links (needs its own revocation story).
- **ADR-028** "Link di conferma e reset senza tabella".

## R2. Invitations

- **Decision**: an `Invitation` table (needed for list, revoke, status). The token is 32 random
  bytes from `secrets.token_urlsafe`; only its SHA-256 is stored; the plain token appears once,
  in the email. Expiry 7 days. Acceptance re-checks that the inviter is still active and still
  has the invited students in scope (covers "inviter loses access" without a revocation hook).
- **Rationale**: invitations have state the user manages; a hashed token means a database leak
  does not leak usable links.
- **Alternatives**: signed links only (cannot be listed or revoked).

## R3. No account enumeration

- **Decision**: register, resend-confirmation and reset-request always answer `202` with the
  same body. Work that depends on existence (sending the email) happens in a Celery task, so
  the response time does not depend on it either. A duplicate registration emails the
  existing owner instead. Sign-in failures (wrong password, unknown email, locked) share one
  generic `401` message.
- **Rationale**: identical content plus moving the slow path off the request removes the
  timing signal (password hashing runs only for real accounts).
- **Alternatives**: identical body but synchronous email (timing leak); CAPTCHA (third party,
  out of scope).

## R4. Lockout

- **Decision**: per-account fields on `User`: `failed_logins`, `lock_level`, `locked_until`.
  Five consecutive failures lock for `15 min * 2**lock_level`, capped at 24 h. Success resets
  `failed_logins` and `lock_level`; a password reset clears the lock. Applied in the token
  serializer before the password check result is revealed. Existing per-IP throttling
  (`THROTTLE_LOGIN`) stays in front.
- **Rationale**: throttling stops one client; the lock stops a distributed guess at one
  account. Updates use `F()` expressions so parallel attempts are counted correctly.
- **Alternatives**: django-axes (dependency, session-oriented, more than needed); lock per IP
  only (already there, insufficient).
- Risk accepted: an attacker can lock a victim out for a while (denial of service on one
  account); the cap and the reset path limit it. Documented in the ADR.

## R5. Second factor (TOTP)

- **Decision**: RFC 6238 TOTP (SHA-1, 6 digits, 30 s, ±1 step) implemented with the standard
  library (`hmac`, `hashlib`, `struct`, `base64`, ~25 lines), tested against the RFC 6238
  test vectors. Secret stored encrypted (R6). The last accepted time step is stored to refuse
  replays. 10 recovery codes, hashed with Django's password hasher, single use.
  Sign-in with MFA on: `POST /auth/token/` answers `200 {"mfa_required": true, "mfa_token"}`
  where `mfa_token` is a `signing` value valid 5 minutes; `POST /auth/mfa/verify/` exchanges it
  plus a code for the JWT pair. Enrolment returns the base32 secret and the `otpauth://` URI;
  the portal shows the secret for manual entry and the URI as a link (no QR library).
- **Rationale**: the algorithm is small and fully specified with official test vectors; no
  dependency to audit. The two-step login keeps the JWT pair out of reach until the second
  factor is checked.
- **Alternatives**: `pyotp` (fine, but a dependency for 25 lines); django-otp (session/admin
  oriented); WebAuthn (better, much bigger scope); SMS (excluded by the spec).
- Deferred: QR code rendering in the portal (add a QR library if owners ask).
- **ADR-029** "Secondo fattore TOTP con la libreria standard".

## R6. Encryption of sensitive fields

- **Decision**: `cryptography`'s `MultiFernet` (AES-128-CBC + HMAC-SHA256, authenticated).
  Keys from `FIELD_ENCRYPTION_KEYS` (comma list, first encrypts, all decrypt). A small
  `EncryptedTextField` in `apps/common/fields.py` encrypts on save and decrypts on load.
  Applied to `Lesson.notes` and to the TOTP secret. Rotation: prepend a new key, deploy, run
  `manage.py rotate_field_keys` (re-encrypts with `MultiFernet.rotate`), then drop the old key.
  Production refuses to start without at least one valid key; dev/test use a fixed test key.
- **Rationale**: the standard library has no authenticated symmetric encryption; `cryptography`
  is the reference Python library and Fernet gives rotation out of the box. Encrypted text
  cannot be searched or sorted — notes are never filtered on, so nothing is lost.
- **Alternatives**: PostgreSQL `pgcrypto` (key travels in every query, ends up in logs);
  django-fernet-fields (unmaintained); disk-level encryption only (does not protect dumps and
  backups).
- **ADR-030** "Cifratura applicativa dei campi sensibili".

## R7. Password hashing

- **Decision**: keep Django's default PBKDF2-SHA256 (1,000,000 iterations in Django 5.2) and
  the existing validators; add the "similar to email" validator check to registration and
  invitation acceptance (already in `AUTH_PASSWORD_VALIDATORS`, now applied with the user).
- **Rationale**: meets OWASP's PBKDF2 recommendation; Argon2 needs `argon2-cffi` and gains
  little at this scale. Load test (phase 4) showed login is CPU-bound already.
- **Alternatives**: Argon2id (recorded as an upgrade path in ADR-027).

## R8. Audit log

- **Decision**: new app `apps/audit` with `AuditEntry` (append-only: `save()` refuses updates,
  `delete()` refused outside the retention task, admin read-only). One function
  `audit.services.record(action, actor, target, studio, outcome, request)` called from the
  services that perform sensitive actions; it copies the request id from the logging context.
  Owner view: `GET /api/v1/audit/` scoped to the owner's studio, paginated, filter by action
  and date. Retention 12 months via Celery beat.
- **Rationale**: explicit calls in services are greppable and testable; signals would fire for
  admin edits and fixtures too and hide the actor.
- **Alternatives**: django-auditlog / simple-history (record every field change, too much
  personal data copied into a second place); database triggers (no actor, no request id).
- **ADR-031** "Audit log scritto dai service".

## R9. Consent, export, erasure, retention

- **Decision**:
  - `ConsentRecord` (parent, students, notice version, given_at, withdrawn_at). The notice
    version is a setting (`PRIVACY_NOTICE_VERSION`) matching the docs file, not a table.
  - Export: synchronous `GET /api/v1/privacy/export/` returning JSON built by a selector from
    the requester's scope (data per family is small: hundreds of rows).
  - Erasure: `POST /api/v1/privacy/erase/` with password. Service in one transaction: deletes
    the user's tokens and consents, anonymises the user (random unusable email, empty names,
    `is_active=False`); for each child with no other linked parent: names replaced with
    "Allievo cancellato #<id>", notes emptied, archived. Payments and lessons keep amounts and
    dates. Blocked while an online checkout for the family is open.
  - Withdrawing consent = erasure of the affected children (same service).
  - Retention task (daily): anonymise archived students 24 months after last activity; delete
    payments older than 10 years; delete audit entries older than 12 months; delete
    unconfirmed self-registrations older than 7 days.
- **Rationale**: anonymisation in place keeps the studio's accounting intact (SC-007).
- **Alternatives**: hard delete with cascade (destroys payment history required for tax);
  asynchronous export by email (unneeded at this data size; reconsider if exports grow).
- **ADR-032** "Cancellazione come anonimizzazione e tempi di conservazione".

## R10. Student role and minors

- **Decision**: `User.Role.STUDENT`; `Student.is_adult` (bool, default false) and
  `Student.user` (nullable one-to-one). `TenantContext` gains `student_id`; `TenantPaths`
  gains a `student` path; `scope()` filters by it. Students only pass `IsAuthenticated` +
  read-only permissions; every write permission already requires teacher/owner.
- **Rationale**: reuses the single scoping choke point (Principle I); a boolean instead of a
  date of birth is data minimisation (FR-019).

## R11. Secret scanning and personal-data-free logs

- **Decision**: CI job `secrets` running the pinned gitleaks binary over the full history
  (`fetch-depth: 0`, `gitleaks git --redact`), with a `.gitleaks.toml` allow-list only for the
  known fake test keys. Log test: run sign-in, reset, invitation and MFA flows under `caplog`
  and Sentry's `before_send` and assert that no email, name, password, code or token appears.
- **Rationale**: the current pre-commit hook covers Stripe keys in new commits only; history
  and other secret types were never scanned.
- **Alternatives**: GitHub secret scanning (only alerts, does not block the change; can be
  enabled by the owner too).

## R12. Transport and cookies

- **Decision**: no change in mechanism; add a test that `prod` settings keep
  `SECURE_SSL_REDIRECT`, HSTS, secure cookies, `SECURE_CONTENT_TYPE_NOSNIFF`, and fail without
  `FIELD_ENCRYPTION_KEYS`. Refresh token in an httpOnly cookie stays deferred (ADR-023).

## R13. Constitution

- **Decision**: add Principle **X. Privacy by Design for Minors' Data** (minimisation, minors
  only through a parent, consent recorded, export/erasure available, encryption of free text
  about students, audit of sensitive actions, no personal data in logs, secrets scanned in
  history). MINOR bump 3.0.1 → 3.1.0 through `/speckit-constitution`.
- **ADR-027** "Principi di sicurezza e privacy".
