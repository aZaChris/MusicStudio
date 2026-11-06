# Tasks: Celery & Online Payments (Phase 3)

**Input**: `specs/004-celery-payments/` · **Tests**: REQUIRED · **Docs/ADR**: REQUIRED

## Phase 1: Setup

- [ ] T001 Add `stripe` dependency (done at specify time) and Stripe settings (`STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CURRENCY`, `CHECKOUT_SUCCESS_URL`, `CHECKOUT_CANCEL_URL`) with test-mode-only validation in `backend/config/settings/base.py`; document in `.env.example` and both Compose files
- [ ] T002 Celery reliability settings and beat schedule in `backend/config/settings/base.py` and `backend/config/celery.py`

## Phase 2: Foundational

- [ ] T003 `backend/apps/payments/gateway.py`: the only Stripe-importing module (`create_checkout_session`, `retrieve_checkout_session`, `verify_event`, `PaymentsUnavailable`); fake gateway fixture in `backend/apps/payments/tests/fakes.py`
- [ ] T004 Models `CheckoutSession`, `WebhookEvent`, `Payment.Method.CARD`, `Payment.checkout` + migration in `backend/apps/payments/`

## Phase 3: US1 — Checkout (P1) 🎯

- [ ] T005 [P] [US1] Tests: link returned, reuse open attempt, expired attempt → new one, already paid 409, outside tenant 404, unavailable 503, idempotency key passed, live key refused, in `backend/apps/payments/tests/test_checkout.py`
- [ ] T006 [US1] `start_checkout` service + `POST /packages/{id}/checkout/` action

## Phase 4: US2 — Webhook + reconciliation (P1)

- [ ] T007 [P] [US2] Tests: valid signed event → one payment; same event ×3 → one payment; bad/missing signature 400 and nothing stored; async unpaid then async_payment_succeeded; async_payment_failed; expired; unknown checkout; unhandled type; amount from Stripe; reconciliation of missed completion and expiry, in `backend/apps/payments/tests/test_webhooks.py`
- [ ] T008 [US2] `StripeWebhookView`, `record_webhook_event`, `process_webhook_event` task, `apply_session_state`/`fulfil`, `reconcile_open_checkouts` task

## Phase 5: US3 — Reminder outbox (P2)

- [ ] T009 [P] [US3] Tests: sweep ×N → one delivery per parent; send failure → retried, one email; stale lease re-claimed; cancelled lesson skipped; max attempts → failed, in `backend/apps/notifications/tests/test_reminders.py`
- [ ] T010 [US3] `ReminderDelivery` model + migration; outbox services and tasks; remove the at-most-once claim

## Phase 6: US4 — Celery reliability (P2)

- [ ] T011 [US4] Test asserting reliability settings and that every task is registered with retry policy where relevant in `backend/config/tests/test_celery.py`

## Phase 7: US5 — Dashboard cache (P2)

- [ ] T012 [P] [US5] Tests: second request ≤ 2 queries; write in studio → fresh; other studio unaffected; parent not cached; cache failure falls back, in `backend/apps/lessons/tests/test_dashboard_cache.py`
- [ ] T013 [US5] `backend/apps/lessons/cache.py` + signals in `backend/apps/common/signals.py`

## Phase 8: US6 — Docs

- [ ] T014 [P] [US6] ADR-013 (Stripe Checkout, test mode), ADR-014 (webhook store-then-process), ADR-015 (reminder outbox, supersedes ADR-008), ADR-016 (Celery reliability), ADR-017 (cache versioning)
- [ ] T015 [P] [US6] Concepts: `task-celery-idempotenti.md`, `webhook-idempotenti.md`, `pagamenti-online-stripe.md`, `caching.md`
- [ ] T016 [US6] Glossary, Q&A, overview, index, OWASP walk (API6, API10), ADR-008 status → superseded, KB if needed

## Phase 9: Polish

- [ ] T017 Pre-commit Stripe-key detector; regenerate `openapi.yaml`; full gate; README; phase 3 summary commit
- [ ] T018 Copy docs to `doc_music_studio/Fase 3 - Celery e pagamenti` + refresh `00 Generale`

## Dependencies
Setup → Foundational → US1 → US2 → (US3, US4, US5) → US6 → Polish.
