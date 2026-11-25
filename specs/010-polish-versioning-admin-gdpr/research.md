# Research: Polish phase

Facts below were read from the repository on 2026-11-23 unless marked otherwise.

## R1. How to signal a deprecation

- **Decision**: a decorator `@deprecated(since=..., sunset=..., successor=...)` for DRF views.
  It adds `Deprecation: true`, `Sunset: <HTTP date>` (RFC 8594) and, when given,
  `Link: <successor>; rel="successor-version"` to every response, and sets `deprecated: true` on
  the operation through drf-spectacular. After the sunset date the view answers `410 Gone`
  with the project's normal error envelope and code `endpoint_gone`.
- **Why**: headers are what generic HTTP clients and API gateways already understand; the
  contract flag shows up in generated clients and in the Swagger page at no cost.
- **Alternatives**: URL versioning with a second `v2` tree now (nothing breaks yet, so it would
  be speculative); DRF's `NamespaceVersioning` (adds machinery for a version that does not
  exist); a `Warning` header (obsolete).
- **Open point**: the standard `Deprecation` header value is an HTTP date or `true`; `true`
  is the form used in the draft many gateways accept. Check the current RFC text before
  writing the policy and say in the ADR which form was chosen.

## R1b. Making a deprecation impossible to forget (owner's request, 2026-11-23)

Headers and the OpenAPI flag are read by machines. The owner worries that nobody sees them. So
the signals get a human side too:

- **Register**: `docs/operations/deprecations.md`, one row per deprecation (announced, removal
  date, replacement, migration report, status). The decorator keeps an in-code registry; a test
  fails when an item of the registry has no row, no report file, or less than 90 days of notice.
  Source of truth is the code; the Markdown is checked against it, so the two cannot drift.
- **Reminder with an expiry**: a management command `deprecation_report` prints each
  deprecation with days left and the calls in the last 30 days. A scheduled GitHub Actions
  workflow (weekly) runs it and **fails when 30 days or less remain** (or the date passed and
  the code is still there). A red scheduled run reaches the owner by GitHub's own failure email
  and does not block pull requests. Chosen over a failing test in the normal pipeline, which
  would turn unrelated PRs red on a calendar date.
- **Who still uses it**: every call logs one structured line (`deprecated_call`, endpoint,
  client name and version from a header if present, request id). The numbers in the report come
  from the logs where they are kept; if logs are not queryable on this deployment, the
  report says "unknown" instead of guessing.
- **Migration report**: template `docs/operations/migrations/TEMPLATE.md`, one filled copy
  per deprecation, plus `mobile-followup.md`-style note for the `mobile` branch. Sections: what
  changes and why, affected clients, old vs new request and response, steps for web portal,
  steps for mobile, other clients, test checklist, timeline with the three dates (announced,
  warning, removal), rollback, and how to move to a *different service* when the replacement is
  not a new version (what the new service is, how to authenticate, data mapping, cut-over).
- **Why**: a deprecation that nobody can find or is reminded of is worse than no policy; it
  becomes a surprise outage on the removal date.
- **Alternatives**: calendar entry only (outside the repo, personal, lost); a GitHub issue per
  deprecation with a milestone (good, but needs a person to create it; can be added later if the
  register is not enough); failing test on the date in the normal CI (blocks unrelated work).

## R2. How to catch breaking contract changes

- **Decision**: a CI job that generates the contract from the branch, takes
  `backend/openapi.yaml` from `main`, and runs `oasdiff breaking`. It fails on any error-level
  finding. A reviewed exception is a line in `.github/oasdiff-ignore.txt` with the reason and
  the PR link, so a breaking change is always a visible decision.
- **Why**: oasdiff understands OpenAPI semantics (removed field, narrowed enum, new required
  request field) which a text `diff` cannot; no Python dependency is added.
- **Alternatives**: writing our own comparison (a project of its own, easy to get wrong);
  `openapi-diff` (Java runtime in CI); only the existing `diff -u openapi.yaml` check, which
  proves the file is regenerated but not that the change is safe.
- **Risk**: this runs only in GitHub Actions, so it cannot be fully proved on this machine
  unless the binary is installed. Plan: install the same pinned release locally once, run it
  on two real contract versions (current vs the one before phase 9) and record the output.
  If it cannot be installed, say so in the phase summary.

## R3. Who may use the admin, and how

- **Facts**: the `User` model has roles `teacher`, `studio_owner`, `parent`, `student` and
  Django's standard `is_staff`/`is_superuser`. TOTP lives in `apps/accounts/mfa.py`
  (`check_second_factor`, `is_enabled`, but `is_eligible` covers owners and teachers only).
  Lockout is in `apps/accounts/services.py` (`is_locked`, failure counting). `common/net.py`
  has `client_ip`.
- **Decision**: a subclass of `AdminSite` mounted at `ADMIN_URL`:
  `has_permission` requires `is_active`, `is_staff`, and a studio-less operator account
  (no teacher/owner/parent/student role in use). Its login form adds a one-time code field,
  checked with the existing TOTP service, mandatory when `ADMIN_REQUIRE_TOTP` is true (true in
  production, false in dev and tests unless a test turns it on). Wrong passwords or codes go
  through the same lockout counters as the API. `ADMIN_ALLOWED_IPS` (empty = no restriction)
  refuses other clients with 404.
- **Why**: one place, no new dependency (no `django-otp`), the TOTP code is already
  specified, tested and has recovery codes.
- **Alternatives**: `django-otp` or `django-two-factor-auth` (second TOTP implementation next to
  ours, templates to maintain); VPN or proxy-level auth only (not under our control; useful
  as an extra layer and mentioned in the runbook); disabling the admin and using management
  commands only (loses the read-only inspection the operator uses).
- **Open point**: `is_eligible` must also accept operator accounts, or operators need their own
  rule. Decide when reading `mfa.py` in the implementation task; the test matrix covers it.

## R4. Read-only for final records

- **Decision**: a mixin `FinalRecordAdmin` that returns `False` from the add, change and
  delete permissions and removes bulk delete. Used for `Payment`, `Receipt`,
  `PaymentDispute`, `WebhookEvent`, `CheckoutSession`, `ConsentRecord`, `AuditEntry`
  (already read-only: moves to the mixin). A test enumerates `admin.site._registry` and
  fails if a model of the final list is editable, or if a model is registered that is in
  neither list (final, or explicitly editable).
- **Why**: constitution X and phase 8 say these records are never edited; the admin was the
  one door left open (`admin.site.register(Payment)` today).
- **Alternatives**: remove them from the admin (the operator loses the read view for support);
  rely on the database constraints (they stop some edits but not all, and the admin would
  show confusing errors).

## R5. Audit of admin actions and hiding sensitive fields

- **Decision**: a mixin `AuditedAdmin` overriding `save_model`, `delete_model`,
  `delete_queryset` and a wrapper for custom actions; each writes one entry to the existing
  audit log (`apps/audit`) with new actions `admin.change` and `admin.delete`, the model label,
  the object id (or the count for bulk) and the field names changed, never the values. Admin
  logins are audited as `admin.login`.
- **Hiding**: admins do not list or show `EncryptedTextField` columns (notes, TOTP secret,
  IBAN); a test inspects every registered admin and fails if its `fields`/`list_display`
  reach such a field, or if it has no explicit `fields`/`exclude` for a model that has one.
- **Why**: the audit log is the project's single answer to "who did what"; Django's own
  `LogEntry` is mutable by the superuser and duplicates it.
- **Alternatives**: Django `LogEntry` only (mutable); signals on every model save (also
  catches code writes, noisy, mixes admin and normal traffic).

## R6. Export completeness: how to make it checkable

- **Decision**: `apps/privacy/inventory.py` is a dict from model label (`app.Model`) to either
  `("exported", "<key in the export>")` or `("excluded", "<reason>")`. A test enumerates every
  model of the project apps and fails on a missing entry, naming the model. A second test
  builds a full family and checks that each `exported` key is present and non-empty in the
  result, so the registry cannot lie.
- **Why**: a registry of all models, not only "personal" ones, avoids a hidden judgement call in
  the checker; a developer adding a model must answer the question once, in review.
- **Alternatives**: auto-detect personal data by field names or by foreign keys to `User`
  (misses indirect data like a payment of a child; false confidence); a model attribute
  flag (spreads the answer across files and is easy to forget).

## R7. Gap analysis of the current export (to do first in implementation)

- **Facts read**: `build_export` returns account, children with lessons, packages and payments,
  consents, and for owners the studio block with payment instructions and the connected
  account id.
- **To check against the model list**: receipts of the family's payments (reference only),
  online checkout sessions of the parent, payment disputes and refunds as reversal rows
  (already inside payments?), invitations sent to or by the user, audit entries where the
  user is the actor (right of access), reminder deliveries (`notifications`), lesson notes
  (encrypted: exported decrypted since they are the family's data?), MFA state (enabled yes/no,
  never the secret).
- **Decision**: do the analysis as task one, write each finding into the inventory with its
  reason, then change `build_export` only for real gaps. Never invent a gap: the test output is
  the evidence.

## R8. Large exports

- **Decision**: measure first. Seed one parent, three children, two years of weekly lessons,
  payments and receipts, time `build_export` and the serialisation. If under 10 s (expected,
  since the code uses one query per table), keep it synchronous and say so in the ADR; add a
  `FUTURO (...)` comment for a background export. Build the asynchronous version only if the
  measurement fails.
- **Why**: avoids building a job queue for a problem that may not exist (YAGNI), with the number
  as proof. Two simultaneous requests are already limited by the `privacy` throttle scope.

## R9. Portfolio write-up

- **Decision**: `README.md` keeps to one screen of "what, why, architecture picture, decisions
  with ADR links, measured numbers with date and command, limits, how to run"; the story goes
  to `docs/case-study.md` (English, three problems from `docs/knowledge-base/`). Numbers come
  from commands run in the last task (`pytest` summary, coverage, load-test report in
  `docs/loadtest/`), each with its date. Architecture picture: a Mermaid diagram in Markdown,
  which GitHub renders (no image file to keep in sync).
- **Alternatives**: a separate site (more to maintain, nothing to deploy); screenshots (the
  owner has no browser run of the portal on this machine; do not fake them).

## Findings during implementation (2026-11-25)

### T001 (closes R1 open point)

- Error envelope (`apps/common/exceptions.py`): `{"detail": ..., "code": ...}` produced by
  `DomainError` subclasses. The gone response is a new `EndpointGone(DomainError)` with status
  410 and code `endpoint_gone`, so no new envelope is invented.
- `Deprecation` header form: RFC 9745 (March 2025) standardised the header as a Structured
  Field **Date**, `Deprecation: @<unix seconds>`, the moment the resource is (or was)
  deprecated. The older draft value `true` is not in the RFC. Decision: use the RFC form with
  the `since` date. `Sunset` stays an HTTP-date (RFC 8594). `Link` carries
  `rel="successor-version"` when there is a successor and `rel="deprecation"` (RFC 9745) to the
  policy document. The contract doc is updated accordingly.

### T002 (closes R3 open point)

- `User.role` is a required `CharField` without a default; accounts made with
  `createsuperuser` have `role == ""`. **Operator = active, `is_staff`, `role == ""`.** Studio
  roles never pass the gate even with `is_staff` forced.
- `mfa.is_eligible` accepted only teachers and owners. It now also accepts operators, so an
  operator enrols with the existing API endpoints (`/api/v1/auth/mfa/setup/` and `confirm/`)
  and the admin login checks the code with the existing `check_second_factor`.
- Recovery: the command `reset_mfa <email>` already exists (phase 7) and is audited
  (`mfa.reset_by_operator`). No new command is written (T020 reuses it).
- Lockout: `services.is_locked`, `register_login_failure`, `register_login_success` are reused
  as they are; they already write `login.failure`/`login.locked` audit entries.

### T003 and T015 (R2 proved locally)

- `oasdiff` v1.40.0, linux amd64, downloaded from the GitHub release, checksum verified.
- Real run, contract before phase 9 (`a2a60ec`) vs now, default rules: **13 errors**, all false
  alarms for us: 4 x `response-property-enum-value-added` (new audit actions: the list is meant
  to grow) and 9 x `request-property-all-of-added` (drf-spectacular moved the payment status
  enum into an `allOf` reference, same accepted values).
- Same run with `--flatten-allof` and a severity file that turns
  `response-property-enum-value-added` into a warning: `4 changes: 0 error, 4 warning`, exit 0.
  This is the configuration used in CI (`.github/oasdiff-levels.txt`). Trade-off, recorded in
  ADR-040: a client that switches on an enum without a default branch is not protected by CI;
  the policy tells client developers to always handle unknown values.
- Opposite proof: scratch copy with `Lesson.start_time` renamed: `10 changes: 10 error`
  (`response-required-property-removed` on dashboard, lessons list, create, upcoming...),
  exit 1. The scratch file was never in the repository.

### T031 gap analysis of `build_export` (R7)

Read on 2026-11-25 against every model of `apps.*`. "Gap" means personal data of the requester
(or of their linked children) that we store and the export did not contain.

- Exported already: `accounts.User` (account), `students.Student` and `ParentStudentLink`
  (children), `ParentAccount` (it holds nothing beyond the user), `lessons.Lesson` (notes
  decrypted: they are about the child), `packages.Package`, `payments.Payment`,
  `privacy.ConsentRecord`, and for owners `studios.Studio`, `PaymentInstructions`,
  `StudioPaymentAccount`.
- **Gaps found and closed**:
  - MFA: whether two-step verification is on (`account.mfa_enabled`), never the secret.
  - Receipts: each payment now carries its receipt number (`AAAA-NNNN`), by reference, since
    the PDF is generated on demand (ADR-035).
  - Reversals: each payment carries `reversal_of`, so a refund row is linked to what it
    reverses.
  - Online checkouts created by the user (`online_checkouts`: amount, currency, status, date).
  - Reminder emails sent to the parent (`reminders`: lesson id, status, sent date).
  - Invitations addressed to the user's own email (`invitations`: studio, role, status, date).
    Invitations an owner sent to others are *not* exported: they hold other people's emails.
  - Audit entries where the user is the actor (`activity`: date, action, outcome), as part of
    the right of access. Entries about other people are not included.
- **Excluded on purpose** (reasons in `apps/privacy/inventory.py`): `MfaDevice` secret and
  `RecoveryCode` hashes (credentials), `Teacher` (the teacher's data, not the family's; the
  studio name is exported), `PaymentDispute` (already visible as reversal rows of the payment,
  ADR-038), `WebhookEvent` (scrubbed technical events, ADR-039).

### T035 export timing (R8)

Measured on 2026-11-25 on the development machine (WSL2, PostgreSQL 16 local, test settings),
with a throwaway test that was not committed: 1 parent, 3 children, 104 weekly lessons each
(2 years), a package every 10 weeks, a payment with receipt every 4 weeks.

`build_export` + `json.dumps`, 5 runs: **312 lessons, 78 payments, 85,622 bytes; best 47.0 ms,
worst 166.6 ms**. The limit is 10 s, so the export stays synchronous (no background job, no new
queue). A `FUTURO (export in background)` comment marks the upgrade path in
`apps/privacy/selectors.py`. Query count is fixed per table: the budget test uses two children
and stays under 15 queries for the whole request.
