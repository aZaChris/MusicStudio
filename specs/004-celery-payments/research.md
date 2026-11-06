# Research: Celery & Online Payments (Phase 3)

Sources: Stripe best-practices guidance (Stripe plugin skill, API 2026-09-30.endive,
stripe-python 16.x), stripe-python 16.1.0 installed and inspected locally.

## Which Stripe API
- **Decision**: Checkout Sessions, Stripe-hosted page, `mode=payment`, inline `price_data`.
  ADR-013.
- **Rationale**: Stripe's recommended API for on-session one-time payments; hosted page keeps
  card data off our servers (lowest PCI scope); no Product catalogue needed for per-package
  prices.
- **Alternatives**: PaymentIntents + Payment Element (custom UI the clients don't need yet);
  Payment Links (static, cannot carry our package/attempt id cleanly); Charges API
  (deprecated — never).

## Payment methods
- **Decision**: do not send `payment_method_types`; dynamic payment methods configured in the
  Dashboard.
- **Consequence**: delayed methods (e.g. SEPA Direct Debit) complete the session as
  `unpaid` → must handle `checkout.session.async_payment_succeeded` / `_failed`.

## Fulfilment
- **Decision**: only from webhooks (never the success page); fulfil on `completed` and
  `async_payment_succeeded` when `payment_status != "unpaid"`.
- **Rationale**: customers may never reach the success page.

## Webhook processing
- **Decision**: verify → store by `event.id` (unique) → 200 → Celery task on commit. ADR-014.
- **Rationale**: Stripe retries for days on non-2xx and may deliver duplicates and out of
  order; acknowledging fast avoids timeouts; the unique event id makes duplicates no-ops; the
  task re-reads state and is idempotent so redelivery is harmless.
- **Alternatives**: process inline in the request (slow handler → Stripe retries → more
  duplicates); dedup only by "payment already exists" (works for this event type, not a
  general guarantee).

## Duplicate checkout requests
- **Decision**: persist the attempt row first, then call Stripe with
  `idempotency_key = checkout-<attempt uuid>`; reuse open unexpired attempts.
- **Rationale**: a double click returns the same session; a retry after a network error
  between Stripe and us replays the same Stripe request instead of creating a second session.

## Keys and environments
- **Decision**: env `STRIPE_API_KEY` must start with `sk_test_` or `rk_test_` (restricted key
  recommended); live prefixes abort start-up (constitution IV); missing key → checkout 503.
  Pre-commit hook detects `[sr]k_(test|live)_` strings in code. Separate Stripe sandbox for
  dev and CI is recommended in docs.
- **RAK permissions needed**: Checkout Sessions write.
- **API version**: use the SDK's pinned version (stripe-python 16.1 targets the current
  version); upgrading the SDK is the explicit upgrade path.

## Reminder delivery
- **Decision**: transactional outbox table, one row per (lesson, parent), lease-based claim,
  Celery retries with exponential backoff, max 5 attempts. Supersedes ADR-008. ADR-015.
- **Alternatives**: keep at-most-once (loses reminders on crash); retry the whole sweep
  (re-sends to parents already served).

## Celery reliability
- **Decision**: `acks_late` + `reject_on_worker_lost` + prefetch 1 + time limits. ADR-016.
- **Trade-off**: tasks may run twice after a crash → every task must be idempotent (they are).

## Caching
- **Decision**: per-studio version key in Redis bumped on commit by model signals; dashboard
  key includes version, scope and date; TTL 5 min. ADR-017.
- **Alternatives**: delete keys on write (must know every key → parents/teachers/dates);
  short TTL only (stale after writes); cache invalidation by explicit service calls (misses
  admin and DRF destroy); `cache_page` (per-URL, ignores tenant, unsafe with auth).
