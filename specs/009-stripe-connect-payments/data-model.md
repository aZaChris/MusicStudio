# Data Model: Online Payments Straight to the Studio

All in `apps/payments` unless noted. Names are English; comments will be Italian (CLAUDE.md).
Schema changes and data changes go in separate migrations (a project gotcha).

## New: `StudioPaymentAccount`

One per studio at most.

| Field | Type | Notes |
|---|---|---|
| `studio` | OneToOne `studios.Studio`, CASCADE | the tenant; deleting the studio removes the link, never the money |
| `stripe_account_id` | CharField(64), unique | the studio's own Stripe account (`acct_...`) |
| `state` | CharField, choices | `in_progress`, `information_needed`, `active`, `restricted`, `disconnected` (`not_started` = no row) |
| `state_changed_at` | DateTime | last change, for the audit and the portal |
| `created_by` | FK user, SET_NULL | the owner who started onboarding |
| `created_at`, `updated_at` | DateTime | |

Not stored: identity, bank details, requirements, business name (principle X).
`can_accept_online` is a property: `state == "active"`.

## Changed: `CheckoutSession`

- `stripe_account_id` CharField(64), blank: the account the session was created on. Empty on
  phase 3 rows. Used to read the session back (reconciliation) and to check an event's account.
- `stripe_payment_intent_id` CharField(255), blank, indexed: filled on completion; links refund
  and dispute events to the payment.

## Changed: `WebhookEvent`

- `stripe_account_id` CharField(64), blank, indexed: from the event's `account`; empty for events
  of the platform's own account.
- `livemode` Boolean, default False.
- `outcome` CharField, choices: `pending`, `applied`, `ignored`, `needs_attention`. Set when
  processed. `needs_attention` is a refund or dispute that matches no register entry, or an
  amount that differs from the package; the studio sees these (contract `GET /payment-account/`).
- `payload` stores a **scrubbed** event (research R10); processed events older than 90 days are
  deleted by the retention job.

## Changed: `Payment` (the register)

- `reversal_of`: **OneToOne -> ForeignKey**, `related_name="reversals"` (research R6).
- `cause` CharField, choices `manual` (default), `refund`, `dispute`; only meaningful on reversal
  rows (a check constraint says non-reversal rows keep `manual`).
- `provider_ref` CharField(255), null, **unique**: the Stripe refund or dispute id, so a repeated
  notification is a no-op.
- Constraints: the two of phase 8 stay; added
  - unique `reversal_of` where `cause = 'manual'` (a manual reversal is at most one and is full);
  - `provider_ref` is set exactly when `cause != 'manual'` on a reversal row.
- Invariants kept by the service under a row lock on the original (not expressible as a
  constraint): the sum of the reversal amounts of a payment never exceeds its amount; a manual
  reversal is only allowed when no other reversal exists and has the full amount.
- A payment is **reversed** when its reversals sum to its amount; the register's "effective paid"
  filter and the package paid check use that (new selector `reversed_amount` annotation).
- `method` keeps the stored value `card` (label "Online (Stripe)"): changing it would rewrite
  history for no gain.

## New: `PaymentDispute`

| Field | Type | Notes |
|---|---|---|
| `payment` | FK `Payment`, CASCADE | the paid online entry |
| `stripe_dispute_id` | CharField(255), unique | idempotency |
| `status` | CharField | `open`, `won`, `lost` |
| `amount` | Decimal(8,2) | amount disputed |
| `opened_at`, `closed_at` | DateTime | |

"Under dispute" in the API = the payment has a dispute with status `open`. The payment row itself
is never written (it is final).

## Changed: audit log (`apps/audit`)

New actions in `Action` (choices migration): `payment_account.start`, `payment_account.state`
(actor "provider" = no actor), `payment.refund` (a refund reflected), `payment.dispute`
(opened, won, lost, in the metadata). Existing: `payment.record` for the online payment,
`payment.reverse` for manual reversals. Metadata holds ids, amounts and state names only.

## State transitions

- **Account**: (none) -> `in_progress` on first onboarding; Stripe reports drive the rest
  (`information_needed`, `active`, `restricted`); `disconnected` is terminal for that account id;
  a studio that reconnects gets a new account row after the old one is removed by the owner action
  "start again" (only allowed from `disconnected`).
- **Checkout attempt**: unchanged (`open` -> `completed`, `failed`, `expired`).
- **Payment**: `paid` stays `paid` forever; reversals are added, never edits.
- **Dispute**: `open` -> `won` or `lost`.

## Relationships (summary)

Studio 1-0..1 StudioPaymentAccount. Package 1-n CheckoutSession 0..1-1 Payment. Payment 1-n
reversal Payments (self FK). Payment 1-n PaymentDispute. WebhookEvent refers to accounts and
sessions by Stripe id only (no foreign key: events can name things we do not have).

## Migration plan

1. Schema: create `StudioPaymentAccount`, `PaymentDispute`; add the new columns; alter
   `reversal_of`; add constraints; audit action choices.
2. No data migration: `cause` defaults to `manual`, which is true for every existing reversal.
3. Reverse path: documented (the FK back to OneToOne is only possible while no payment has two
   reversals).
