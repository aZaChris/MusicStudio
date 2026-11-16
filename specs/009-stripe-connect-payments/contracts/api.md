# API contract changes: phase 9

Base path `/api/v1/`. The generated `backend/openapi.yaml` is the source of truth; this file lists
what changes and the behaviour the tests pin down. Errors follow the project format
(`code`, `detail`). A resource of another studio answers `404` (principle I).

## New: the studio's payment account

Roles: the **studio owner** (a teacher working alone is their own owner) can start and refresh;
**teachers of the studio** can read; parents and students get `404`; other studios get `404`.

### `GET /payment-account/`

Reads the database only (no call to Stripe).

```json
{
  "state": "not_started | in_progress | information_needed | active | restricted | disconnected",
  "can_accept_online": false,
  "test_mode": true,
  "dashboard_url": "https://dashboard.stripe.com/test/dashboard",
  "state_changed_at": "2026-11-20T10:00:00Z",
  "needs_attention": [
    {"id": 12, "kind": "refund_unmatched | dispute_unmatched | amount_differs",
     "received_at": "2026-11-21T09:00:00Z", "amount": "40.00"}
  ]
}
```

`needs_attention` lists at most 20 recent items with identifiers and amounts only (no payload, no
names). `dashboard_url` is null until an account exists.

### `POST /payment-account/onboarding/`  (owner only)

Creates the studio's account if none exists (idempotent per studio: a double click gives one
account) and returns where to send the owner.

- `200 {"url": "https://connect.stripe.com/...", "expires_at": "..."}`
- `409 account_disconnected` when the state is `disconnected` (the owner must use `/restart/`).
- `503 payments_unavailable` when Stripe cannot be reached; nothing is stored.
- Audit: `payment_account.start`.

### `POST /payment-account/refresh/`  (owner only)

Reads the account from Stripe and updates the state; called by the portal when the owner returns
from Stripe. `200` with the same body as `GET`. Rate limited (`THROTTLE_PAYMENT_ACCOUNT`).

### `POST /payment-account/restart/`  (owner only, only from `disconnected`)

Removes the dead link so onboarding can start again. `204`; `409` from any other state.

## Changed: `POST /packages/{id}/checkout/`

Same address and same response shape (`checkout_id`, `url`, ...). Differences:

- The session is created **on the studio's account**.
- `409 online_payments_not_available` when the studio's state is not `active`.
- `409 package_already_paid` as today; `404` for a package the caller cannot see.
- Reuse of an open attempt, idempotency key and lock behave as in phase 3.

## Changed: package reads

`GET /packages/` and `/packages/{id}/` gain `can_pay_online` (boolean): true when the studio's
account is active and the package is open. Computed in the queryset (no extra query per row;
query budget test).

## Changed: payment reads

Existing fields keep their meaning. Added to a payment:

- `reversed_amount` (string decimal): sum of its reversals (`"0.00"` when none).
- `under_dispute` (boolean).
- On a reversal row: `cause` (`manual | refund | dispute`).

`is_reversed`/the nested reversal of phase 8 keep working: a payment is "reversed" when
`reversed_amount == amount`; a partly refunded payment shows `reversed_amount < amount`.

`POST /payments/{id}/reverse/` (manual): unchanged, but answers `409 already_reversed` also when a
refund already reduced the payment (a manual reversal is only for a payment with no reversal).

## Register summary and exports

`received`, `reversed` and `net` (per method and overall) add up every reversal row, whatever its
cause. The CSV gains the columns `cause` and `provider_ref` (provider ids are not personal data);
the PDF totals follow the summary. A one-line note in both says that refunds and disputes come from
the payment provider.

## New: Stripe Connect webhook

`POST /webhooks/stripe-connect/`, same rules as `/webhooks/stripe/` (allowlisted source IP, raw
body, signature checked with `STRIPE_CONNECT_WEBHOOK_SECRET`, `200` after storing, work done in the
background): `400` invalid signature, `403` source not allowed. Not in the portal; documented in
the runbook.

## Environment

New: `STRIPE_CONNECT_WEBHOOK_SECRET`, `THROTTLE_PAYMENT_ACCOUNT` (default `20/hour`). Unchanged:
`STRIPE_API_KEY` (test keys only; a live key still stops start-up), `CHECKOUT_*`. The return and
refresh addresses of onboarding derive from `FRONTEND_URL`.

## Mobile

No client calls these today (research R9). A follow-up note `mobile-followup.md` lists
`can_pay_online`, the checkout `409` and the new payment fields for branch `mobile`.
