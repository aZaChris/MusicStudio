# Implementation Plan: Polish — API Versioning, Admin Hardening, Complete Data Export, Portfolio Write-up

**Branch**: `010-polish-versioning-admin-gdpr` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-polish-versioning-admin-gdpr/spec.md`

## Summary

Four independent slices on the existing modular monolith, no new product behaviour:

1. **Versioning and deprecation**: a written policy, a tiny `apps/common/deprecation.py`
   (decorator that adds the standard `Deprecation`, `Sunset` and `Link` response headers and
   marks the operation `deprecated` in the OpenAPI contract; after the sunset date the view
   answers `410` with a stable error code), and a CI job that compares the generated contract
   with the one on `main` and fails on breaking changes (research R1, R2).
2. **Admin hardening**: one custom `AdminSite` gate (active operator only, in production a TOTP
   code on the admin login form reusing `accounts/mfa.py`, same lockout as the API, optional
   IP allowlist reusing `common/net.py`), a read-only mixin for final records, an audit mixin
   that writes to the existing append-only audit log, and a test that fails when a registered
   admin exposes an encrypted field or a final model is editable (R3–R5).
3. **Export completeness**: an explicit inventory of every model (`exported` or `excluded:
   reason`) checked by a test that enumerates `apps.get_models()`, a gap analysis of the current
   `build_export`, and a measurement for the "10 seconds" criterion before deciding whether a
   background export is needed (R6–R8).
4. **Portfolio**: README rewrite, an English case study, numbers taken from commands run on the
   day, Italian study docs, ADRs, OWASP walk and index updates (R9).

## Technical Context

**Language/Version**: Python 3.12, Django (current LTS), DRF, drf-spectacular

**Primary Dependencies**: existing only. No new Python dependency. CI gains one tool
(`oasdiff`, run as a pinned container/action) for contract diffing.

**Storage**: PostgreSQL; one migration only (new audit action choices). No new tables.

**Testing**: pytest + pytest-django + factory_boy against PostgreSQL; coverage floor 90%.

**Target Platform**: Linux server (Coolify, Docker Compose), no change.

**Project Type**: web-service (Django REST API); `frontend/` untouched, `mobile` untouched.

**Performance Goals**: export of 1 parent + 3 children + 2 years of weekly lessons under
10 s (SC-006), measured; admin and deprecation headers add no database query.

**Constraints**: no new endpoints for clients; the contract changes only by `deprecated`
flags and descriptions; all provider calls stay in `apps/payments/gateway.py`.

**Scale/Scope**: about 22 models, 8 admin modules, 1 export endpoint, 1 CI job.

## Constitution Check

*GATE: passes before Phase 0 and again after Phase 1.*

- [x] I. No new tenant data access. The admin is the one place that bypasses tenant scoping, so
      it is gated to operators and tested per role (US2). The export keeps scoping from the
      account (no id in the request); cross-family test is extended.
- [x] II. Nothing leaves `/api/v1/`; the contract stays accurate and is now diff-checked.
- [x] III. Tests ship with each slice; export has a query-count assertion (existing, extended).
- [x] IV. Roadmap phase 5 (polish); previous phases are complete.
- [x] V. Helpers in `apps/common` (cross-cutting); privacy logic in `apps/privacy/selectors.py`;
      admin classes stay in each app's `admin.py`; mypy clean.
- [x] VI. `frontend/` unchanged; `mobile` untouched; `web`/`app` tags untouched.
- [x] VII. CI gets one more job (contract diff); the rest unchanged.
- [x] VIII. ADR-040 (versioning policy and contract diff), ADR-041 (operator-only admin with
      TOTP), ADR-042 (export inventory); Italian concept docs and index updates planned.
- [x] IX. OWASP walk updated: API9 (improper inventory management) gets the deprecation policy,
      API8 (misconfiguration) the admin hardening.
- [x] X. Export completeness is principle X made testable; admin never shows decrypted fields;
      export is audited.

No violations, so the Complexity Tracking table is empty.

## Project Structure

### Documentation (this feature)

```text
specs/010-polish-versioning-admin-gdpr/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── deprecation-and-errors.md
├── checklists/requirements.md
└── tasks.md            # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/common/
│   ├── deprecation.py          # NEW: decorator, in-code registry, usage log, 410 (R1, R1b)
│   ├── management/commands/deprecation_report.py   # NEW: days left, calls in 30 days (R1b)
│   ├── admin_site.py           # NEW: OperatorAdminSite, login form with TOTP, IP allowlist (R3)
│   ├── admin_mixins.py         # NEW: FinalRecordAdmin (read-only), AuditedAdmin (R4, R5)
│   └── tests/                  # test_deprecation.py, test_admin_gate.py, test_admin_inventory.py
├── apps/<each>/admin.py        # use the mixins; list columns and filters; no sensitive fields
├── apps/audit/models.py        # new Action values: admin.change, admin.delete, admin.login
├── apps/privacy/
│   ├── inventory.py            # NEW: model -> exported/excluded + reason (R6)
│   ├── selectors.py            # completed after the gap analysis (R7)
│   └── tests/test_export_inventory.py, test_export_completeness.py
├── config/urls.py              # admin mounted on the operator site
├── config/settings/{base,prod}.py   # ADMIN_REQUIRE_TOTP, ADMIN_ALLOWED_IPS, API_SUNSET_* none
└── openapi.yaml                # regenerated (no breaking change expected)
.github/workflows/ci.yml        # contract-diff job (R2)
docs/operations/api-versioning-policy.md        # the written policy (English, for client devs)
docs/operations/deprecations.md                 # register, checked against the code (R1b)
docs/operations/migrations/TEMPLATE.md          # migration report template (version or service)
.github/workflows/deprecation-watch.yml         # weekly, red at 30 days or less (R1b)
docs/learning/                  # ADR-040..042, 2 concept docs, glossary, Q&A, index, OWASP walk
README.md, docs/case-study.md   # portfolio (English)
```

**Structure Decision**: modular monolith unchanged; cross-cutting code goes to `apps/common`
(constitution V), the per-model admin tweaks stay in each app.

## Complexity Tracking

*No constitution violations to justify.*
