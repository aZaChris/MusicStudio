# Implementation Plan: Online Payments Straight to the Studio (Stripe Connect)

**Branch**: `009-stripe-connect-payments` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-stripe-connect-payments/spec.md`

## Summary

Make an online payment land on the studio's own Stripe account instead of the platform's, in four
slices that reuse the phase 3 checkout and the phase 8 register:

1. **Studio account**: a new `StudioPaymentAccount` (one per studio) created and onboarded through
   Stripe's hosted pages; the portal shows its state. Only an `active` account can receive payments.
2. **Paying online**: the existing `POST /packages/{id}/checkout/` creates the Checkout Session
   *on the studio's account* (direct charge, no fee, `Stripe-Account` header). The webhook records
   the paid entry exactly as today, now attributed to the studio account named by the event.
3. **Refunds and disputes**: a second webhook endpoint for connected accounts turns a succeeded
   refund or a lost dispute into **reversal rows** of the phase 8 register. To support partial
   refunds, `Payment.reversal_of` becomes a foreign key with a `cause` and a unique `provider_ref`.
4. **Hygiene**: stored webhook events are scrubbed of personal data and expire after 90 days; the
   phase 3 platform-account path is gone; studios without an account behave exactly as in phase 8.

No money passes through MusicStudio, no fee is taken, nothing is paid out. Everything runs in
**Stripe test mode**. Choices and rejected alternatives: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12, Django 5.2, DRF (existing); TypeScript 5 / React 19 (portal)

**Primary Dependencies**: existing stack and the `stripe` SDK already locked (`>=12`). No new
dependency. Whether the locked version covers the calls of the spike is checked first (R12); the
gateway raises the minimum if needed.

**Storage**: PostgreSQL 16 (CI also 18). Two new tables (`StudioPaymentAccount`, `PaymentDispute`),
new columns on `CheckoutSession`, `WebhookEvent` and `Payment`, one FK change on `Payment`. One
schema migration, one for audit action choices; no data migration ([data-model.md](data-model.md)).

**Testing**: pytest + factory_boy on real PostgreSQL with the fake gateway (`tests/fakes.py`) and
real-shaped event fixtures; Vitest + Testing Library for the portal; one recorded sandbox run.

**Target Platform**: Linux server (Docker on Coolify); modern browsers.

**Project Type**: web service (Django API) + SPA (`frontend/`).

**Performance Goals**: package and payment lists keep a constant query count with the new fields;
webhook acknowledgement stays a single insert, with the work in Celery.

**Constraints**: every Stripe call inside `apps/payments/gateway.py`; test keys only (live key stops
start-up); no personal or financial data from Stripe in logs, error reports, the audit log or stored
events; the registered paid entry stays immutable; the mobile app breaks nowhere.

**Scale/Scope**: a studio sees a handful of online payments a month; 4 user stories, 34
requirements, 4 new endpoints, 1 new webhook route, 2 new portal pages.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [X] I. Every new endpoint scopes reads and writes by studio (`scope()`/`TenantContext`);
  `404` across studios; the webhook attributes by account id, never by a client-supplied studio.
  Cross-studio read and write tests are planned for each endpoint.
- [X] II. Everything is under `/api/v1/` and in the generated OpenAPI; the portal uses the generated
  types.
- [X] III. Tests ship in the same change: permission boundaries, idempotency (replays, concurrent
  threads), the reversal sum invariant, query budgets on `GET /packages/` and `GET /payment-account/`.
  Coverage floor 90% holds.
- [X] IV. **Passes, with a note.** Payment gateway integration is allowed in *Stripe test mode
  only*; this feature stays in test mode, so no amendment is needed. Going live is explicitly out of
  scope and needs a MINOR amendment (owner task T-owner-3). The principle's list of phases (1-5) is
  stale since phases 6-8; a one-line PATCH is proposed together with the go-live amendment.
- [X] V. Writes in `services.py` (account lifecycle, checkout, event application, reversals), reads
  in `selectors.py` (state, `reversed_amount`, `can_pay_online`); thin views; mypy clean. The new
  account code is one module pair inside `payments`, no new app (the account belongs to payments).
- [X] VI. Types regenerated from `openapi.yaml`; tests with the network mocked at `fetch`; EN/IT
  text via i18next. `web` and `app` tags untouched.
- [X] VII. CI unchanged in shape: ruff, mypy, migrations-in-sync, pytest, OpenAPI check, frontend
  job.
- [X] VIII. Three ADRs planned (037 account type and charge type, 038 reversals as a foreign key,
  039 scrubbed event store and a second webhook endpoint) and Italian study docs (below).
  **Note**: the constitution still says comments are English while CLAUDE.md (owner's decision of
  2026-11-14) says Italian; this feature follows CLAUDE.md and proposes aligning the wording of
  Principle VIII with it.
- [X] IX. OWASP walk updated at the end (broken object level authorization on the new endpoints;
  unrestricted resource consumption on onboarding; unsafe consumption of a third-party API:
  webhooks authenticated, idempotent and attributed).
- [X] X. **Privacy by design holds and improves.** Only the account id and a state are stored; the
  owner's email is not sent to Stripe; stored events are scrubbed and expire (R10); logs and the
  audit log carry identifiers and amounts only; the studio account row is removed with the studio;
  the owner's data export includes the account id and state.

**Re-check after Phase 1 design**: unchanged. The one structural risk is the foreign-key change on
`Payment` (R6): the phase 8 guarantee "one reversal per payment" is kept for manual reversals by a
partial unique constraint, and the new invariant (sum of reversals <= amount) is enforced under a
row lock with a concurrency test, the same pattern as receipt numbers.

## Project Structure

### Documentation (this feature)

```text
specs/009-stripe-connect-payments/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md              # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/apps/payments/
├── gateway.py            # + create_account, create_account_link, retrieve_account;
│                         #   Stripe-Account header on checkout create/retrieve; verify_event(secret)
├── models.py             # + StudioPaymentAccount, PaymentDispute; columns; reversal_of -> FK
├── services.py           # + account lifecycle, checkout on the studio account, refund/dispute
│                         #   application, scrubbed event store, reversal sum invariant
├── selectors.py          # + reversed_amount annotation, can_pay_online, account state read
├── account_views.py      # new: GET/POST payment-account, onboarding, refresh, restart
├── webhooks.py           # + StripeConnectWebhookView (shared store-then-process path)
├── tasks.py              # + retention purge of processed events (nightly job)
├── serializers.py        # + fields (reversed_amount, under_dispute, cause); account serializer
├── urls.py               # + routes
└── tests/                # + test_account_*.py, test_connect_*.py, test_refunds.py,
                          #   test_disputes.py, test_event_scrub.py, fixtures/ (real-shaped events)
backend/apps/audit/       # + four action choices (migration)
backend/apps/packages/    # checkout action now 409s without an active account; can_pay_online
backend/apps/students/    # selectors/serializers move from `reversal__isnull` to the new selector
backend/apps/common/      # factories (reversal rows), privacy export of the account id and state
backend/config/settings/  # STRIPE_CONNECT_WEBHOOK_SECRET, THROTTLE_PAYMENT_ACCOUNT, test rates
docker-compose.coolify.yml, .env.example, docs/operations/runbook.md   # new variables, endpoint
frontend/src/features/
├── teacher/PaymentAccount.tsx      # owner's settings: state, start/resume, Stripe Dashboard link
├── parent/ParentPortal.tsx         # "Pay online" next to open packages when can_pay_online
├── payments/ReturnPages.tsx        # success / cancel / onboarding return (refresh then redirect)
└── ... tests, i18n strings (EN/IT), generated schema
specs/009-stripe-connect-payments/mobile-followup.md   # note for branch `mobile`
docs/learning/                      # concept file, ADR-037/038/039, glossary, Q&A, OWASP, index
```

**Structure Decision**: extend the existing `payments` app and the existing portal features; no new
Django app (the account is part of the payment domain and shares the gateway, the event store and
the register). One new backend module for the account views to keep `views.py` readable.

## Order of work (feeds `/speckit-tasks`)

1. **Spike** (needs the owner's sandbox): settle research R12; record results in `research.md`;
   save real event payloads (scrubbed) as fixtures. Nothing below starts before items 1 and 2 of
   R12 are answered.
2. **Schema and register change** (R6): migrations, `reversed_amount` selector, adapt the ten
   places, concurrency tests. Phase 8 tests must pass unchanged in meaning.
3. **Gateway and account** (slice 1): account functions, `StudioPaymentAccount`, endpoints, audit,
   state derivation, tests with the fake gateway.
4. **Paying online** (slice 2): checkout on the account, `can_pay_online`, event attribution,
   reconciliation with the account id, webhook for the platform endpoint kept.
5. **Connect webhook, refunds, disputes** (slice 3): second endpoint, event application, dispute
   table, `needs_attention`, idempotency and concurrency tests.
6. **Event hygiene** (slice 4): scrub, 90-day purge, tests with a personal-data-laden event.
7. **Portal**: owner page, parent button, return pages, tests, generated types, i18n.
8. **Docs and close-out**: runbook and compose variables, ADRs, concept file, glossary, Q&A, OWASP
   walk, index and "Riepilogo della fase 9", mobile follow-up, NotebookLM export (phase checklist
   of CLAUDE.md), sandbox run recorded.

## Risks and what the owner must provide

- **Sandbox and platform profile (blocks step 1).** The owner creates a Stripe sandbox, enables
  Connect, creates the Connect webhook endpoint and passes the keys through the environment (never
  in chat). Whether test mode needs the platform profile completed is part of the spike.
- **PayPal is not guaranteed** (research R8). The owner's goal mentions it; the plan delivers cards
  and the wallets Stripe enables for the account, and records what the sandbox shows.
- **Standard accounts are labelled legacy by Stripe** (R1). Mitigated by the gateway boundary and
  the spike.
- **Real money stays out** until T-owner-1 to T-owner-3 of the spec are done.
- **Partial refunds touch phase 8 code** (R6): the biggest regression risk, covered by keeping the
  phase 8 test suite as the safety net and adding the concurrency tests first.

## Complexity Tracking

No violation of the constitution. Two choices add cost on purpose and are justified in ADRs:
the foreign-key change on `Payment.reversal_of` (needed for partial refunds, which the spec requires
to be reflected) and a second webhook endpoint (Stripe delivers connected-account events only to a
different endpoint kind with its own secret).
