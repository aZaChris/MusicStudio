# Data Model: Security, Privacy and Accounts (Phase 007)

Changes to existing models and new models. Schema changes and data migrations go in separate
migrations (CLAUDE.md gotcha: PostgreSQL refuses ALTER TABLE with pending deferred FK checks).

## accounts.User (changed)

| Field | Type | Notes |
|---|---|---|
| role | + `student` choice | `teacher`, `studio_owner`, `parent`, `student` |
| email_verified | bool, default False | data migration sets True for every existing user |
| failed_logins | positive int, default 0 | consecutive failures |
| lock_level | positive smallint, default 0 | lock duration = 15 min × 2^level, cap 24 h |
| locked_until | datetime, null | sign-in refused while in the future |
| terms_accepted_at | datetime, null | set at registration / invitation acceptance |

Rules: sign-in requires `is_active` and `email_verified`. Erasure sets `is_active=False`,
empties names, replaces the email with `erased-<uuid>@invalid` and sets an unusable password.

## accounts.Invitation (new)

| Field | Type | Notes |
|---|---|---|
| studio | FK Studio | tenant of the invitation |
| invited_by | FK User | must still be active and in scope at acceptance |
| email | email | lower-cased |
| role | choice | `teacher`, `parent`, `student` |
| students | M2M Student | parents: one or more; student: exactly one (`is_adult`) |
| token_hash | char(64), unique | SHA-256 of the emailed token |
| expires_at | datetime | created + 7 days |
| status | choice | `pending` → `accepted` / `revoked`; `expired` is derived from `expires_at` |
| accepted_by | FK User, null | |
| created_at | datetime | |

Validation: teacher may invite only `parent`/`student` for students in their scope; owner may
invite any role in their studio; `student` requires the student to be adult and without an
account; one pending invitation per (studio, email, role) (partial unique constraint).

## accounts.MfaDevice (new)

| Field | Type | Notes |
|---|---|---|
| user | O2O User | owners and teachers only |
| secret | EncryptedTextField | base32 TOTP secret |
| confirmed_at | datetime, null | device active only once confirmed with a valid code |
| last_used_step | bigint, default 0 | TOTP step of the last accepted code (anti-replay) |

## accounts.RecoveryCode (new)

| Field | Type | Notes |
|---|---|---|
| device | FK MfaDevice, cascade | 10 per device; regenerated together |
| code_hash | char(64) | SHA-256 of the code (random, 50 bits: a slow hash adds cost, not safety) |
| used_at | datetime, null | single use |

## students.Student (changed)

| Field | Type | Notes |
|---|---|---|
| is_adult | bool, default False | set by the teacher; no date of birth stored |
| user | O2O User, null, SET_NULL | the adult student's own account |
| anonymised_at | datetime, null | set by erasure / retention |

## lessons.Lesson (changed)

| Field | Type | Notes |
|---|---|---|
| notes | EncryptedTextField | was TextField; data migration encrypts existing rows |

## privacy.ConsentRecord (new app `apps/privacy`)

| Field | Type | Notes |
|---|---|---|
| parent | FK ParentAccount, null, SET_NULL | null after the parent's erasure |
| students | M2M Student | children covered |
| notice_version | char(20) | value of `PRIVACY_NOTICE_VERSION` at the time |
| given_at | datetime | |
| withdrawn_at | datetime, null | withdrawal triggers erasure of the children (if no other parent) |

## audit.AuditEntry (new app `apps/audit`)

| Field | Type | Notes |
|---|---|---|
| created_at | datetime, indexed | |
| actor | FK User, null, SET_NULL | null for anonymous attempts and system jobs |
| action | choice | see list below |
| outcome | choice | `success`, `failure`, `denied` |
| studio | FK Studio, null, SET_NULL, indexed | scope for the owner view |
| target_type | char(40) | e.g. `user`, `student`, `payment`, `invitation` |
| target_id | bigint, null | identifier only, never names or emails |
| request_id | char(64) | from the logging context |
| metadata | JSON, default {} | non-personal details (e.g. lock level, role) |

Append-only: updates raise; deletes only through the retention task. Index
`(studio, created_at desc)`.

Actions: `login.success`, `login.failure`, `login.locked`, `password.reset`,
`password.change`, `email.confirm`, `mfa.enable`, `mfa.disable`, `mfa.recovery_used`,
`mfa.reset_by_operator`, `account.unlock_by_operator`, `invitation.send`,
`invitation.accept`, `invitation.revoke`, `role.change`, `consent.give`, `consent.withdraw`,
`privacy.export`, `privacy.erase`, `payment.record`, `registration`.

## State transitions

- **Self-registered owner**: `unconfirmed` → (link within 48 h) `active`; `unconfirmed` older
  than 7 days → deleted with its studio.
- **Account lock**: `open` → 5 failures → `locked(level n)` → expiry → `open` (level kept) →
  success → level reset.
- **Invitation**: `pending` → `accepted` | `revoked`; `pending` past `expires_at` = expired.
- **Student data**: `active` → archived → (24 months without activity, or erasure)
  `anonymised`.
