# Implementation Plan: Celery & Online Payments (Phase 3)

**Branch**: `refactor/production-standards` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

## Summary

Add Stripe Checkout (test mode only) for lesson packages, fulfilled exclusively through
signature-verified webhooks that are stored once by event id and processed by an idempotent,
retrying Celery task, with an hourly reconciliation for missed events. Replace the
at-most-once reminder claim with a per-(lesson, parent) outbox sent with retries. Harden
Celery (late ack, one-at-a-time prefetch, time limits). Cache the studio dashboard with
version-key invalidation driven by model signals.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.2, DRF, Celery 5.6 + Redis, **stripe-python 16.1**
(`StripeClient`; API version pinned by the SDK), drf-spectacular

**Storage**: PostgreSQL 16 (new tables: `payments_checkoutsession`, `payments_webhookevent`,
`notifications_reminderdelivery`); Redis (broker, cache)

**Testing**: pytest; Stripe calls behind `apps/payments/gateway.py`, replaced by a fake in
tests; webhook signatures produced with the real HMAC-SHA256 scheme and verified by the real
SDK; `django_capture_on_commit_callbacks` for on-commit task dispatch; Celery eager mode

**Constraints**: test-mode keys only (`sk_test_`/`rk_test_`); live keys abort start-up;
never send `payment_method_types`; fulfil only when `payment_status != "unpaid"`

**Scale/Scope**: low volume (a few hundred checkouts/month per studio)

## Constitution Check

- [x] I. Checkout scoped by the package queryset (404 outside tenant); webhook endpoint
  carries no tenant, it resolves the checkout by provider id
- [x] II. New endpoints under `/api/v1/`, contract regenerated
- [x] III. Tests for every failure mode in the spec; query budget for cached dashboard
- [x] IV. Phase 3 explicitly re-opens payment gateway, **test mode only**
- [x] V. Provider isolated in a gateway module; logic in services; tasks thin
- [x] VI. No client code
- [x] VII. Pre-commit gains a Stripe key detector
- [x] VIII. ADR-013…017, four concept docs
- [x] IX. OWASP walk: API6 (business flow), API10 (unsafe consumption) now apply

## Project Structure (changes)

```text
backend/apps/payments/
├── gateway.py        # the only module importing stripe: create/retrieve session, verify event
├── models.py         # + CheckoutSession, WebhookEvent; Payment.Method.CARD, Payment.checkout
├── services.py       # + start_checkout, record_webhook_event, apply_session_state, reconcile
├── tasks.py          # process_webhook_event (retrying, idempotent), reconcile_open_checkouts
├── views.py          # + StripeWebhookView (no auth, no throttle, raw body)
backend/apps/packages/views.py      # + POST /packages/{id}/checkout/
backend/apps/notifications/
├── models.py         # ReminderDelivery (outbox)
├── services.py       # enqueue_due_reminders, send_delivery (claim with lease)
├── tasks.py          # sweep + send_reminder_delivery (autoretry, backoff)
backend/apps/lessons/cache.py        # dashboard cache, studio version keys
backend/apps/common/signals.py       # bump studio cache version on writes
backend/config/celery.py, settings   # reliability settings, beat schedule, Stripe settings
```

## Implementation approach

- **Checkout (US1)**: `start_checkout(package, ctx)`: refuse if a paid payment exists (409);
  reuse an open, unexpired `CheckoutSession` for the package; else create the Stripe session
  via the gateway with `idempotency_key=f"checkout-{attempt.uuid}"` (row created first, so a
  retried request after a network error reuses the same key), `mode=payment`, inline
  `price_data` (EUR, cents), `metadata.checkout_id`, `client_reference_id`,
  `integration_identifier`, success/cancel URLs from settings, `expires_at` 30 min.
- **Webhook (US2)**: raw body + `Stripe-Signature` → `gateway.verify_event` (400 on failure)
  → `WebhookEvent.objects.get_or_create(stripe_event_id=...)` → on create,
  `transaction.on_commit(process_webhook_event.delay(pk))` → 200. Task locks the event row,
  returns if processed, applies by type: `completed` / `async_payment_succeeded` with
  `payment_status != unpaid` → `fulfil(checkout)`; `async_payment_failed` → failed;
  `expired` → expired. `fulfil` locks the checkout row and creates the single `Payment`
  (`OneToOne` from Payment to CheckoutSession = DB-level "at most one payment per attempt").
- **Reconciliation (US2)**: hourly beat task: open sessions past `expires_at` → gateway
  retrieve → same `apply_session_state`.
- **Reminder outbox (US3)**: sweep `bulk_create(ignore_conflicts=True)` on unique
  `(lesson, parent)`; dispatch pending deliveries; `send_delivery` claims with a conditional
  UPDATE (`pending` or stale `sending` lease older than 10 min → `sending`), re-checks the
  lesson is still scheduled, sends, marks `sent`; on error sets back `pending` with attempt
  count and lets Celery retry with exponential backoff (max 5) → then `failed`.
- **Celery (US4)**: `task_acks_late`, `task_reject_on_worker_lost`,
  `worker_prefetch_multiplier=1`, soft/hard time limits, JSON serializer, beat schedule
  (reminder sweep 15 min, reconciliation hourly).
- **Cache (US5)**: key `dashboard:v1:{studio}:{version}:{role}:{teacher}:{date}`; version per
  studio in the cache, bumped by `post_save`/`post_delete` signals on Lesson, Package, Payment,
  Student (on commit); TTL 300 s; parents uncached; cache errors fall back to computing.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| Signals for cache invalidation | must catch every write path (admin, DRF destroy, services) | explicit calls in services miss admin and `destroy` |
