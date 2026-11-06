# API Contract Changes: Celery & Online Payments (Phase 3)

## POST /api/v1/packages/{id}/checkout/
Auth: any user who can see the package (teacher, owner, parent of the student).
Request: empty. Responses:
- 200 `{"checkout_id": "<uuid>", "url": "https://checkout.stripe.com/...", "expires_at": "..."}`
  (same body for repeated calls while the attempt is open)
- 404 package not visible · 409 `{"code": "package_already_paid"}` · 503
  `{"code": "payments_unavailable"}` (no Stripe key or Stripe unreachable)

## POST /api/v1/webhooks/stripe/
No authentication, no throttling. Body: raw Stripe event JSON; header `Stripe-Signature`.
- 200 `{"received": true}` (also for duplicates and unhandled types)
- 400 invalid payload or signature (nothing stored)

## Payments
- `method` enum gains `card`; response gains read-only `checkout` (uuid or null).
