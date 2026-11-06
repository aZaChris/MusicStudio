# Quickstart / Validation: Celery & Online Payments (Phase 3)

## Automated (no Stripe account needed)
`uv run pytest -k "checkout or webhook or reconcile or delivery or dashboard_cache or celery"`

## Manual, with a Stripe sandbox (recommended: a dedicated sandbox for dev)
1. Create a sandbox (`stripe sandbox create`, or Dashboard → Sandboxes) and a **restricted
   key** with "Checkout Sessions: write". Put it in `.env` as `STRIPE_API_KEY=rk_test_...`.
2. `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe/` → copy the
   `whsec_...` into `STRIPE_WEBHOOK_SECRET`.
3. `docker compose up` (worker + beat included). `POST /api/v1/packages/<id>/checkout/` → open
   the URL, pay with test card `4242 4242 4242 4242`.
4. Check: one `Payment` with method `card`, status `paid`, linked to the checkout.
5. `stripe events resend <evt_id>` → still one payment.
6. Stop `stripe listen`, pay another package, wait for the hourly reconciliation (or call
   `reconcile_open_checkouts` from a shell after expiry) → payment recorded.

Not run while building phase 3 (no Stripe account, no Docker in the authoring environment);
the automated suite covers each step with a fake gateway and real signature verification.
