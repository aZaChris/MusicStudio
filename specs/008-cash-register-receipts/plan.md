# Implementation Plan: Studio Cash Register, Payment Instructions and Receipts

**Branch**: `008-cash-register-receipts` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-cash-register-receipts/spec.md`

## Summary

Make the existing `payments` app a trustworthy register, in three slices that share one table:

1. **Register integrity**: a paid entry becomes final (no edit, no delete). A mistake is fixed by a
   *reversal entry*: a new `Payment` row of status `reversal`, linked one-to-one to the original,
   with reason, actor and date. The original row is never written again, so a closed month cannot
   change. Pending and overdue entries stay editable and removable (their removal is audited).
2. **Register views and export**: a period summary (received, reversed, net, per method) computed
   in SQL, the existing payments list gains date filters, and two exports (CSV and PDF) for one
   period of at most one year. Days and months follow the studio's local date.
3. **Payment instructions and receipts**: one set of instructions per studio (IBAN and holder
   encrypted at rest), shown to parents beside their open packages; a non-fiscal PDF receipt per
   paid entry with a gapless number per studio and year.

No money moves through the product, the Stripe code is untouched, and no tax document is issued.
The approach reuses what exists: `scope()` for tenancy, `EncryptedTextField` for secrets, the audit
log for traceability, `select_for_update` on a studio row for gapless numbers. The only new
dependency is a PDF library (reportlab). Details and rejected alternatives: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12, Django 5.2, Django REST Framework (existing); TypeScript 5 / React 19 for the portal

**Primary Dependencies**: existing stack + `reportlab` (PDF, BSD licence, wheels, no system libraries). IBAN checksum and CSV use the standard library (research R2, R3).

**Storage**: PostgreSQL 16 (CI also 18). Two new tables (`PaymentInstructions`, `Receipt`) and four new columns on `Payment`. One migration for schema, one for audit action choices; no data migration (existing rows stay valid, FR-034).

**Testing**: pytest + pytest-django + factory_boy against real PostgreSQL; Vitest + Testing Library for the portal

**Target Platform**: Linux server (Docker image on Coolify); modern browsers

**Project Type**: web service (Django API) + SPA client (`frontend/`)

**Performance Goals**: register for a month with 2,000 entries shown in under 3 s (SC-003); one-year export of 5,000 entries in under 10 s (SC-004); constant query count on every new list endpoint

**Constraints**: all totals in SQL (no Python loops over entries); exports built in memory (a year of entries is a few hundred KB); no bank details in logs, Sentry events or the audit log; no breaking change for the mobile app (research R9)

**Scale/Scope**: a studio has up to 10 teachers and a few thousand payments a year; 4 user stories, 34 requirements, about 12 endpoints

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] I. Reads AND writes scoped per tenant; cross-tenant read/write tests planned. Every new queryset goes through `scope()` (`Receipt` gets its own `TenantPaths`); instructions are keyed by the caller's own studio, never by an id from the request. Cross-studio tests for every endpoint (FR-032).
- [x] II. Feature reachable via `/api/v1/`, OpenAPI accurate. See [contracts/api.md](contracts/api.md); `backend/openapi.yaml` regenerated, SPA types regenerated.
- [x] III. Tests in the same change; query-count assertions on main endpoints. Query budgets on the register list, summary, instructions and receipts list; concurrency tests for reversal (FR-009) and receipt numbers (SC-007).
- [x] IV. Within the current roadmap phase. This is a new phase opened by the owner (spec 008); the roadmap row in `CLAUDE.md` is added with this plan. No gateway code is touched (Stripe stays test mode, all calls in `gateway.py`).
- [x] V. Logic in `services.py` / `selectors.py`; thin views/serializers; mypy clean. Rendering (CSV, PDF) lives in two small pure modules, `exports.py` and `pdf.py`, called by views; no HTTP in services.
- [x] VI. Web client (`frontend/`): generated types, rotating-token session, tests; `web`/`app` untouched. Register page, instructions page, parent block and receipt downloads use the existing API client; bilingual EN/IT; downloads go through the authenticated client (no token in URLs).
- [x] VII. CI (ruff, mypy, migrations check, pytest) green. New dependency is added with `uv` and the Docker build is checked by the existing `backend-image` job.
- [x] VIII. ADRs for non-trivial decisions; Italian study docs + index update planned. ADR-034 (register by reversal), ADR-035 (receipts and gapless numbering), ADR-036 (payment instructions: no bank verification, encrypted at rest); concept docs `registro-di-cassa.md`, `ricevute-non-fiscali.md`; glossary, Q&A, index, NotebookLM export.
- [x] IX. Security impact considered (OWASP API Top 10). BOLA on every id, mass assignment (reversal fields read-only), CSV formula injection (FR-015), SSRF-free link handling (links are stored and shown, never fetched), unrestricted resource consumption (period cap, export throttle), sensitive data in logs (Sentry sensitive path). Walk updated at the end.
- [x] X. Privacy: minimal data, minors via parent, export/erasure, encrypted free text, audit, no PII in logs. Receipt carries no payer data (FR-029); reversal reason (free text) is encrypted; IBAN and holder encrypted; owner export and erasure cover the instructions; erased families show an anonymised label with amounts kept.

No violations. Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/008-cash-register-receipts/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and rejected alternatives
├── data-model.md        # Phase 1: tables, constraints, state rules
├── quickstart.md        # Phase 1: how to see it working end to end
├── contracts/
│   └── api.md           # Phase 1: endpoints and the change of mutation rules
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── payments/
│   │   ├── models.py            # Payment (+reversal_of, reason, recorded_by, REVERSAL),
│   │   │                        #   PaymentInstructions, Receipt
│   │   ├── services.py          # reverse_payment, delete_payment, update_payment (final rule),
│   │   │                        #   save_instructions, issue_receipt
│   │   ├── selectors.py         # register_entries, register_summary, open_packages,
│   │   │                        #   instructions_for_parent, receipts_for
│   │   ├── exports.py           # CSV writer with formula neutralisation (new)
│   │   ├── pdf.py               # register summary PDF and receipt PDF (new)
│   │   ├── iban.py              # IBAN format and mod-97 checksum, stdlib only (new)
│   │   ├── serializers.py       # PaymentSerializer (+fields), instructions, receipt, summary
│   │   ├── views.py             # PaymentViewSet: final rule on update/destroy, `reverse` action
│   │   ├── register_views.py    # summary, export csv, export pdf (new)
│   │   ├── instruction_views.py # owner/teacher read-write, parent read (new)
│   │   ├── receipt_views.py     # issue, list, pdf (new)
│   │   ├── urls.py
│   │   └── tests/               # one module per slice, plus concurrency and leak tests
│   ├── packages/ students/      # package_is_paid and latest_payment_status ignore reversed rows
│   ├── audit/                   # new actions: payment.reverse, payment.delete, register.export,
│   │                            #   instructions.change, receipt.issue
│   ├── common/                  # IsTeacherOrOwnerRole moved here from accounts; sentry sensitive path;
│   │                            #   TenantPaths for receipts
│   └── privacy/                 # owner export and erasure cover the instructions
├── config/settings/base.py      # throttle scope `register_export`
└── openapi.yaml                 # regenerated

frontend/src/
├── features/teacher/Payments.tsx          # becomes the register: period, totals, reverse, export, receipt
├── features/team/PaymentInstructions.tsx  # owner edits, teachers read (new)
├── features/parent/ParentPortal.tsx       # instructions beside open packages, receipts list
├── api/schema.d.ts                        # regenerated
└── i18n/                                  # EN and IT strings

docs/learning/                   # ADR-034..036, concept docs, glossary, Q&A, index, export script
```

**Structure Decision**: stay inside the existing modular monolith. The register, the instructions
and the receipts all hang off `Payment`, so they live in the `payments` app rather than a new one
(Principle V: one app per business domain). Views are split by slice into separate modules, as
`accounts` already does with `invitation_views.py`, to keep `views.py` thin. Rendering helpers
(`exports.py`, `pdf.py`, `iban.py`) are pure functions without HTTP or ORM access, so they are easy
to test alone.

## Design decisions in one page

- **Reversal is a new row, never an edit** (research R1). `Payment.reversal_of` is a one-to-one
  to the original, so "at most once" and "exactly one under concurrency" are guaranteed by the
  database, not only by code. The original keeps `status = paid`; "reversed" is derived from the
  link. That is what keeps a closed month unchanged (FR-002, FR-003, FR-009).
- **Totals**: received = paid rows by their date; reversed = reversal rows by their (later) date;
  net = received − reversed. One SQL aggregate per request (research R4).
- **"Open package" = no paid entry that is not reversed.** `package_is_paid`, the roster's
  `latest_payment_status` and the new parent selector all use the same rule (research R5).
- **Final means final in the services, and the API says so with 409** (research R6). Model-level
  guards are not added: bulk `QuerySet` writes bypass them anyway, as with the audit log. The
  retention job is the one deliberate bulk delete and is documented as such in ADR-034.
- **Receipt numbers**: lock the studio row, take `max(sequence) + 1` for the current local year,
  insert; a rollback gives the number back, so there are no gaps (research R7).
- **Receipt content is rendered on demand** from live data plus the stored number and language, not
  stored as a file or a snapshot. A snapshot of a name would survive an erasure request.
- **Instructions for parents** come from one endpoint that lists, per studio with at least one
  open package of the caller's students, the instructions. The page joins it to packages by
  studio, so the number of queries does not grow with the number of packages (research R8).

## Risks and open points

- **Mobile app**: it lists and creates payments only; `PATCH`/`DELETE` of paid entries are not
  called (research R9). The change is still documented in the contract, and `mobile-followup.md`
  gets a note when implementing.
- **CSV in Italian spreadsheets**: semicolon separator and UTF-8 with BOM are chosen for Excel with
  an Italian locale; the choice is debatable and recorded as such (research R3).
- **10-year retention** (`run_retention` deletes old payments): receipts of deleted payments go
  with them; numbers are never reused because they are taken from the maximum of the year.
- **Legal text** (terms of use saying the platform holds no money and issues no tax documents) is
  outside this feature, as the spec assumes.
- **Dependency choice** (reportlab) is confirmed in task T001 by installing it and building the
  image; if the wheel were a problem, `fpdf2` is the fallback.

## Complexity Tracking

No violations to justify.
