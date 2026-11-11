# Implementation Plan: Security, Privacy and Accounts (Phase 007)

**Branch**: `staging/backend` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-security-privacy-accounts/spec.md`

## Summary

Make accounts self-service and safe, and make privacy for minors' data enforceable: owner
sign-up with email confirmation, invitations for teachers, parents and adult students, reset
without enumeration, per-account lockout, optional stdlib TOTP, recorded consent, export and
erasure by anonymisation, a daily retention job, an append-only audit log written by the
services, Fernet encryption of lesson notes and TOTP secrets, IDOR tests on every endpoint,
secret scanning of the full history, and a log test proving no personal data leaks. A new
constitution principle (X) and ADR-027..032 record the decisions; the portal gets the screens.
Mobile screens follow on `staging/mobile` against the same API.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5 strict (portal)

**Primary Dependencies**: Django 5.2, DRF, simplejwt, Celery, drf-spectacular; **new:**
`cryptography` (Fernet, R6). Portal: React 19, TanStack Query, react-router, i18next; no new
dependency.

**Storage**: PostgreSQL 16; Redis for throttling, cache and Celery

**Testing**: pytest + pytest-django + factory_boy on real PostgreSQL; new `idor` marker; Vitest
+ Testing Library for the portal

**Target Platform**: Linux containers on Coolify; portal served by nginx

**Project Type**: web service + SPA (mobile app on a separate branch)

**Performance Goals**: no regression on phase-4 load test numbers; query budgets on new list
endpoints (`invitations/`, `audit/`, `privacy/consents/`)

**Constraints**: no AWS, Stripe test mode only and no payment test by Claude, no SMS, emails via
Django backend (console in dev, SMTP in prod), 2.7 GB dev machine (Vitest ≤ 2 workers)

**Scale/Scope**: 1–10 teachers per studio, hundreds of students; 8 user stories, 28 FRs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] I. Reads AND writes scoped per tenant; cross-tenant read/write tests planned — student role
  added to `scoping.py`; invitations validate student ids against the scoped queryset; US4 adds
  an IDOR suite over every endpoint.
- [x] II. Feature reachable via `/api/v1/`, OpenAPI accurate — contract in `contracts/api.md`,
  `openapi.yaml` regenerated.
- [x] III. Tests in the same change; query-count assertions on main endpoints — every task ships
  tests; budgets on the three new lists.
- [x] IV. Within the current roadmap phase — phase 007 opened by the owner on 2026-11-11 before
  phase 5 polish; GDPR export moves here from phase 5 (recorded in ADR-027).
- [x] V. Logic in `services.py` / `selectors.py`; thin views/serializers; mypy clean — new apps
  `audit` and `privacy` follow the same layout.
- [x] VI. Web client: generated types, rotating-token session, tests — new pages use generated
  types; MFA step plugs into the existing login flow.
- [x] VII. CI green — plus a new `secrets` job.
- [x] VIII. ADRs for non-trivial decisions; Italian study docs + index update planned —
  ADR-027..032 and concept docs listed below.
- [x] IX. Security impact considered — this phase is the security work; OWASP walk updated at
  the end.

Post-design re-check: still all green. One amendment: Principle X added via
`/speckit-constitution` (MINOR → 3.1.0) as the first task.

## Project Structure

### Documentation (this feature)

```text
specs/007-security-privacy-accounts/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── accounts/        # User fields, Invitation, MfaDevice, RecoveryCode; services for
│   │                    # register/confirm/reset/lockout/mfa/invitations; totp.py (stdlib);
│   │                    # commands unlock_account, reset_mfa
│   ├── audit/           # NEW: AuditEntry, services.record, selectors, owner view, retention
│   ├── privacy/         # NEW: ConsentRecord, export selector, erase service, retention task,
│   │                    # run_retention command
│   ├── common/          # fields.py (EncryptedTextField), scoping (student path),
│   │                    # tenancy (student_id), rotate_field_keys command
│   ├── students/        # is_adult, user, anonymised_at
│   └── lessons/         # notes encrypted
├── config/              # settings: FIELD_ENCRYPTION_KEYS, PRIVACY_NOTICE_VERSION, token
│                        # timeouts, throttle scopes; celery beat: retention, audit purge
└── templates/emails/    # confirmation, reset, password changed, invitation, duplicate signup (IT/EN)

frontend/src/
├── auth/                # Register, ConfirmEmail, ForgotPassword, ResetPassword, MfaStep,
│                        # AcceptInvitation
├── features/account/    # NEW: password change, MFA setup/recovery codes
├── features/team/       # NEW: owner team + invitations; teacher parent/student invitations
├── features/privacy/    # NEW: consents, export, erasure (parent, adult student)
├── features/student/    # NEW: read-only view for adult students
└── features/audit/      # NEW: owner audit list

docs/
├── privacy/             # NEW (Italian): registro-trattamenti.md, informativa-famiglie.md,
│                        # informativa-insegnanti.md — marked DRAFT, versioned
└── learning/            # ADR-027..032; concepts: account-e-token-monouso, mfa-totp,
                         # cifratura-dei-campi, gdpr-per-sviluppatori, audit-log; OWASP walk

.github/workflows/ci.yml # + secrets job (gitleaks, full history)
.gitleaks.toml           # allow-list for the known fake test keys
```

**Structure Decision**: existing modular monolith; two new domain apps (`audit`, `privacy`)
because audit entries and consent/erasure are their own domains used by several apps. The
portal adds feature folders next to `teacher/` and `parent/`.

## Delivery order

1. Constitution X + ADR-027; `cryptography`; `EncryptedTextField` + key settings; audit app
   (everything else records into it).
2. US4 IDOR suite on existing endpoints (baseline before touching auth).
3. US1 registration + confirmation; US2 reset + password change; US3 invitations + consent.
4. US5 lockout + MFA; US6 export/erasure/retention; US7 student role; US8 audit view.
5. Log PII test, secret scanning job, prod-settings test.
6. Portal screens per story, i18n IT/EN, tests.
7. Privacy drafts, study docs, OWASP walk, index, phase summary, NotebookLM export.

## Risks

- **Scope**: largest phase so far. Stories are independent; if time runs short, P3 (US7, US8
  view) moves to a follow-up, never US4.
- **Encrypting existing notes**: data migration runs once; tested on a copy of the restore-drill
  dump size (78k lessons) for duration.
- **Account lock as denial of service**: accepted, capped at 24 h, operator unlock (R4).
- **Legal**: drafts are not legal advice; the owner has a validation task before real families.

## Complexity Tracking

No constitution violations to justify.
