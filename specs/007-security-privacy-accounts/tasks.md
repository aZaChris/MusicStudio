# Tasks: Security, Privacy and Accounts (Phase 007)

**Input**: `specs/007-security-privacy-accounts/` · **Tests**: REQUIRED (constitution III) ·
**Docs/ADR**: REQUIRED (VIII) · 👤 = needs the owner. Backend paths are under `backend/`,
portal paths under `frontend/`. One commit per task (or per tightly coupled pair).

## Phase 1: Setup

- [X] T001 Constitution: add Principle X "Privacy by Design for Minors' Data" via `/speckit-constitution` (3.0.1 → 3.1.0, Sync Impact Report, plan template gate X) in `.specify/memory/constitution.md`; ADR-027 `docs/learning/adr/ADR-027-principi-sicurezza-e-privacy.md` (incl. PBKDF2 kept, Argon2 as upgrade path, GDPR export moved from phase 5)
- [X] T002 Add `cryptography` with `uv add` in `backend/pyproject.toml`; settings `FIELD_ENCRYPTION_KEYS` (list; test/dev fixed Fernet key; prod required and validated at start-up), `PRIVACY_NOTICE_VERSION`, `PASSWORD_RESET_TIMEOUT=3600`, `EMAIL_CONFIRM_MAX_AGE`, `INVITATION_DAYS=7`, `FRONTEND_URL` (links in emails), throttle scopes `register`, `password_reset`, `mfa`, `invitation_accept` in `config/settings/base.py`, `prod.py`, `test.py`; document all in `.env.example` and `docker-compose.coolify.yml`
- [X] T003 [P] Register pytest marker `idor` in `backend/pyproject.toml`; email templates base layout (IT/EN, plain text + HTML) in `backend/templates/emails/`

## Phase 2: Foundational (blocks all stories)

- [X] T004 `EncryptedTextField` (MultiFernet, encrypt on save, decrypt on load, empty string stays empty) in `backend/apps/common/fields.py` + tests (round trip, stored value is not plaintext, old key still decrypts after rotation) in `backend/apps/common/tests/test_fields.py`
- [X] T005 Command `rotate_field_keys` (re-encrypts every encrypted field in batches with `MultiFernet.rotate`) in `backend/apps/common/management/commands/rotate_field_keys.py` + test
- [X] T006 `Lesson.notes` → `EncryptedTextField`: schema migration, then a separate data migration encrypting existing rows, in `backend/apps/lessons/migrations/`; test that notes read back unchanged through the API and raw SQL shows `gAAAA`
- [X] T007 New app `apps/audit`: `AuditEntry` model (append-only `save`/`delete` guards, index `(studio, created_at)`), `services.record(...)` taking actor/action/target/studio/outcome/metadata and the request id from `apps/common/logging.py`, read-only admin, in `backend/apps/audit/`; tests (append-only, request id captured, no extra fields accepted)
- [X] T008 `TenantContext.student_id` + `User.Role.STUDENT` + `Student.is_adult`, `Student.user`, `Student.anonymised_at` (schema migration) + `TenantPaths.student` and student branch in `scope()` in `backend/apps/common/tenancy.py`, `backend/apps/common/scoping.py`, `backend/apps/accounts/models.py`, `backend/apps/students/models.py`; tests for the new branch (student sees only self)
- [X] T009 `User` fields `email_verified`, `failed_logins`, `lock_level`, `locked_until`, `terms_accepted_at`: schema migration, then data migration setting `email_verified=True` for existing users, in `backend/apps/accounts/migrations/`
- [X] T010 Email sending helper: Celery task `send_account_email(kind, user_id|email, context)` rendering the templates in the user's language, logging only kind + user id, in `backend/apps/accounts/emails.py` and `backend/apps/accounts/tasks.py` + tests (locmem outbox, language)

## Phase 3: US4 — Nobody sees what is not theirs (P1) 🎯 baseline first

- [X] T011 [US4] IDOR fixture world: two studios, two teachers per studio, two families, adult student, in `backend/apps/common/tests/idor_world.py`
- [X] T012 [US4] Parametrised IDOR suite (`@pytest.mark.idor`) over every existing endpoint (students, lessons, packages, payments, checkout, dashboard, studio, studio/teachers): read, list, update, delete and related-field writes across teacher/teacher, studio/studio, parent/parent → 404 / rejected and nothing written, in `backend/apps/common/tests/test_idor.py`; fix any gap found (record it in the OWASP doc)
- [X] T013 [US4] Guard test: every URL pattern under `/api/v1/` is either in the IDOR table or in an explicit "no tenant data" allow-list, so a new endpoint without IDOR coverage fails the build, in `backend/apps/common/tests/test_idor_coverage.py`

## Phase 4: US1 — A studio owner signs up alone (P1)

- [X] T014 [US1] Services `register_owner` (creates user unverified + studio + owner teacher in one transaction; duplicate address → "someone tried" email instead), `confirm_email`, `resend_confirmation` using signed tokens (R1) in `backend/apps/accounts/services.py`; audit `registration`, `email.confirm`
- [X] T015 [US1] Endpoints `auth/register/`, `auth/confirm-email/`, `auth/confirm-email/resend/` (uniform 202, throttled) in `backend/apps/accounts/views.py`, `serializers.py`, `urls.py`; sign-in refuses unverified accounts (`code: email_not_confirmed` only after a correct password)
- [X] T016 [P] [US1] Tests: uniform responses for new/existing address (body equal), confirmation single-use and expiry (freezegun or `signing` max_age), unverified login refused, password validators with user attributes, throttle, in `backend/apps/accounts/tests/test_registration.py`
- [X] T017 [US1] Retention of unconfirmed sign-ups (7 days, deletes user + studio) as part of `apps/privacy` retention (stub task now, completed in T040) — test in `backend/apps/accounts/tests/test_registration.py`
- [ ] T018 [US1] Portal: `Register`, `ConfirmEmail` (reads `uid`/`token` from URL), "resend" on login when unconfirmed; routes in `frontend/src/App.tsx`; i18n IT/EN; regenerate `openapi.yaml` + `npm run api:types`
- [ ] T019 [P] [US1] Portal tests: register success/validation errors, confirm ok/expired, login unconfirmed shows resend, in `frontend/src/auth/register.test.tsx`

## Phase 5: US2 — Recover a forgotten password safely (P1)

- [X] T020 [US2] Services `request_password_reset` (uniform, email via task), `reset_password` (token check, set password, revoke all refresh tokens via existing `revoke_sessions` logic, clear lock, "password changed" email), `change_password` (current password, revoke other sessions) in `backend/apps/accounts/services.py`; audit `password.reset`, `password.change`
- [X] T021 [US2] Endpoints `auth/password-reset/`, `auth/password-reset/confirm/`, `auth/password/change/` in `backend/apps/accounts/views.py`
- [X] T022 [P] [US2] Tests: uniform body, link valid 1 h and single-use, older link invalid after newer use, sessions revoked (old refresh rejected), lock cleared, emails sent, in `backend/apps/accounts/tests/test_password_reset.py`
- [ ] T023 [US2] Portal: `ForgotPassword`, `ResetPassword`, password change in `frontend/src/features/account/AccountPage.tsx` + tests `frontend/src/auth/reset.test.tsx`

## Phase 6: US3 — Owners invite teachers and parents (P1)

- [X] T024 [US3] `Invitation` model (hashed token, partial unique pending constraint, M2M students) + migration in `backend/apps/accounts/models.py`
- [X] T025 [US3] New app `apps/privacy` with `ConsentRecord` model + migration in `backend/apps/privacy/`
- [X] T026 [US3] Services `create_invitation` (role rules, students validated against the scoped queryset, adult check), `revoke_invitation`, `lookup_invitation`, `accept_invitation` (inviter still active and in scope; new account verified with chosen password, or links added to signed-in existing account; parent consent recorded with `PRIVACY_NOTICE_VERSION`; teacher → `Teacher` row in studio; student → `Student.user`) in `backend/apps/accounts/services.py` and `backend/apps/privacy/services.py`; audit `invitation.*`, `consent.give`, `role.change`
- [X] T027 [US3] Endpoints `invitations/` (list/create), `invitations/{id}/revoke/`, `invitations/lookup/`, `invitations/accept/` with scoped querysets, query budget on the list, in `backend/apps/accounts/views.py`; add to IDOR table (T012)
- [X] T028 [P] [US3] Tests: owner/teacher permissions per role, out-of-scope student "does not exist", minor refused for student role, 7-day expiry, single use, revoke, inviter removed → refused, existing parent gets links not duplicate, consent recorded, in `backend/apps/accounts/tests/test_invitations.py`
- [ ] T029 [US3] Portal: owner `features/team/TeamPage.tsx` (teachers + pending invitations, invite, revoke); teacher "Invita genitore" on `StudentDetail`; `auth/AcceptInvitation.tsx` (lookup, password, consent checkbox with link to notice); tests `frontend/src/features/team/team.test.tsx`

## Phase 7: US5 — Sign-in that resists guessing and theft (P2)

- [X] T030 [US5] Lockout in a custom `TokenObtainPairSerializer`: generic 401 for wrong/unknown/locked, `F()` counter updates, lock 15 min × 2^level capped 24 h, reset on success; audit `login.success|failure|locked`, in `backend/apps/accounts/serializers.py` + tests (parallel attempts counted, 6th correct attempt refused, unknown email same body) in `backend/apps/accounts/tests/test_lockout.py`
- [X] T031 [US5] `totp.py` (RFC 6238 stdlib: secret generation, `otpauth://` URI, verify with ±1 step and `last_used_step`) + tests with the RFC 6238 SHA-1 vectors in `backend/apps/accounts/totp.py`, `backend/apps/accounts/tests/test_totp.py`; ADR-029
- [X] T032 [US5] `MfaDevice` (secret encrypted), `RecoveryCode` models + migration; services setup/confirm/disable/regenerate codes/verify login; two-step login (`mfa_required` + signed `mfa_token` 5 min) and `auth/mfa/*` endpoints in `backend/apps/accounts/`; audit `mfa.*`
- [X] T033 [P] [US5] Tests: owners/teachers only, confirm required, login without code gives no tokens, replayed code refused, recovery code single use, disable requires password+code, expired `mfa_token`, throttle, in `backend/apps/accounts/tests/test_mfa.py`
- [X] T034 [US5] Commands `unlock_account`, `reset_mfa` (audited) in `backend/apps/accounts/management/commands/` + tests; runbook section in `docs/operations/runbook.md`
- [ ] T035 [US5] Portal: MFA step in `auth/Login.tsx` (code or recovery code), `features/account/MfaSetup.tsx` (secret shown for manual entry, `otpauth` link, confirm, recovery codes shown once with copy/download); locked/generic messages; tests `frontend/src/features/account/mfa.test.tsx`

## Phase 8: US6 — Families control their data (P2)

- [X] T036 [US6] Export selector building the family JSON (account, children, lessons with notes decrypted only for the family's own children, packages, payments, consents) with a query budget, endpoint `privacy/export/` (attachment), audit `privacy.export`, in `backend/apps/privacy/selectors.py`, `views.py`
- [X] T037 [US6] Erase service: password check, 409 while a checkout is open, revoke sessions, anonymise user, anonymise each child with no other linked parent (names → "Allievo cancellato #id", notes emptied, archived, `anonymised_at`), keep payments/lessons amounts and dates, notify teacher when one parent of two leaves; owner erasure only for an empty studio; audit `privacy.erase`, in `backend/apps/privacy/services.py`; ADR-032
- [X] T038 [US6] Consents list and withdraw (password; triggers erase of affected children) endpoints `privacy/consents/`, `privacy/consents/{id}/withdraw/`, in `backend/apps/privacy/views.py`; add privacy endpoints to the IDOR table
- [X] T039 [P] [US6] Tests: export contains 100% own data and 0 of the other family (seeded world), erased person's name/email not found anywhere in the database, studio payment totals unchanged, two-parent child kept, open checkout 409, owner with active studio 409, sign-in fails after erasure, in `backend/apps/privacy/tests/`
- [X] T040 [US6] Retention: `privacy.tasks.run_retention` (archived students 24 months → anonymise; payments > 10 years → delete; audit > 12 months → delete; unconfirmed sign-ups > 7 days → delete) + command `run_retention` + daily beat entry in `backend/config/celery.py`; tests with frozen time
- [ ] T041 [US6] Portal: `features/privacy/PrivacyPage.tsx` (consents with withdraw, download export, erase account with password and clear warning) for parent and adult student; tests `frontend/src/features/privacy/privacy.test.tsx`

## Phase 9: US7 — Adult students see their own lessons (P3)

- [ ] T042 [US7] `is_adult` writable and `has_account` read-only on the student serializer; student role read-only on students/lessons/packages/payments (permissions unchanged for writes; tests that every write is 403 and reads are self-only) in `backend/apps/students/serializers.py`, `backend/apps/common/tests/test_student_role.py`; add student role to the IDOR table
- [ ] T043 [US7] Portal: "Maggiorenne" toggle in `StudentFormDialog`, "Invita allievo" for adult students, `features/student/StudentHome.tsx` read-only, role routing in `auth/RequireRole.tsx`; tests

## Phase 10: US8 — The owner can see who did what (P3)

- [ ] T044 [US8] Audit list endpoint `audit/` (owner only, own studio, filters action/since/until, paginated, query budget) in `backend/apps/audit/selectors.py`, `views.py`; tests incl. teacher/parent 403 and other studio invisible; add to IDOR table
- [ ] T045 [US8] Check every action in the data-model list is recorded by its service (one test per action) in `backend/apps/audit/tests/test_coverage.py`; record `payment.record` in `backend/apps/payments/services.py`
- [ ] T046 [US8] Portal: `features/audit/AuditPage.tsx` (table, action/date filters, translated action names) + tests

## Phase 11: Cross-cutting security

- [ ] T047 PII-free logs: test running register, reset, invitation, MFA and login flows under `caplog` and Sentry `before_send`, asserting no email, name, password, code or token in any record, in `backend/config/tests/test_no_pii_in_logs.py`; fix any leak
- [ ] T048 Secret scanning: `secrets` job in `.github/workflows/ci.yml` (checkout `fetch-depth: 0`, pinned gitleaks binary with checksum, `gitleaks git --redact`), `.gitleaks.toml` allow-list for known fake test keys; run it locally over the full history and record the result
- [ ] T049 Prod settings test: SSL redirect, HSTS, secure cookies, nosniff, refuses start without `FIELD_ENCRYPTION_KEYS`, in `backend/config/tests/test_prod_settings.py`
- [ ] T050 Mobile follow-up note: list of endpoints and screens the app needs, in `specs/007-security-privacy-accounts/mobile-followup.md` (implemented later on `staging/mobile`)

## Phase 12: Privacy drafts and study docs

- [ ] T051 [P] Italian drafts marked "BOZZA — da validare", versioned with `PRIVACY_NOTICE_VERSION`: `docs/privacy/registro-trattamenti.md`, `docs/privacy/informativa-famiglie.md`, `docs/privacy/informativa-insegnanti.md`; portal links them
- [ ] T052 [P] ADR-028 (link senza tabella), ADR-030 (cifratura campi), ADR-031 (audit log dai service) in `docs/learning/adr/`
- [ ] T053 [P] Concept docs (800–1500 words, format in CLAUDE.md): `account-e-token-monouso.md`, `mfa-totp.md`, `cifratura-dei-campi.md`, `gdpr-per-sviluppatori.md`, `audit-log.md` in `docs/learning/concetti/`
- [ ] T054 OWASP API Top 10 walk updated (BOLA results from US4, broken auth, sensitive data) in `docs/learning/concetti/sicurezza-api-owasp.md`; glossary, interview Q&A, overview, `00-indice.md` ("Riepilogo della fase 7")

## Phase 13: Polish

- [ ] T055 Full gate green (ruff, mypy, migrations, pytest ≥ 90%, spectacular, portal typecheck/lint/test/build/api:check); quickstart walk; tasks marked; CLAUDE.md status
- [ ] T056 Add phase to `scripts/export-study-docs.sh` and run it; vault decisions; summary commit "Complete phase 7: ..."
- [ ] T057 👤 Owner: have the privacy drafts validated by a professional before real families use the product
- [ ] T058 👤 Owner: confirm on staging that confirmation/reset/invitation emails arrive from the SMTP provider (CHECKLIST_17 step 2)

## Dependencies

T001–T003 → T004–T010 (Foundational) → US4 baseline (T011–T013) → US1 → US2 → US3 →
US5 → US6 → US7 → US8 → T047–T050 → docs → polish.
US1, US2 and US5's TOTP module (T031) touch different files and can overlap; US3 needs
`apps/privacy` (T025) before consent; US6 needs US3's consents; US7 needs T008 and US3's
invitations; US8's view needs every story's audit calls (T045 checks them).

## Parallel examples

- After T010: T016 (registration tests), T022 (reset tests) and T031 (TOTP module) are
  independent files.
- Docs T051–T053 can be written while portal tasks run.

## Implementation strategy

MVP = Foundational + US4 + US1 + US2 + US3: a real owner can sign up, invite a teacher and
parents, recover a password, and nothing crosses tenants. Commit after each task; push at the
end of each story when the full gate is green. If time runs short, US7 and US8's view move to
a follow-up; US4 never does.
