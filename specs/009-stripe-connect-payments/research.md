# Research: Online Payments Straight to the Studio (Stripe Connect)

Decisions taken while planning phase 9. Sources: Stripe's Connect documentation (charges, accounts,
Accounts v2, direct charges, webhooks, testing) read on 2026-11-16, Stripe's PayPal and
payment-method-support pages, and the existing code of `apps/payments`. Where a fact came from a
third-party page only, it is marked **to verify**: the first task of the implementation is a short
spike in a Stripe sandbox that settles every item marked so (see R12).

## R1 - Which kind of connected account

> **REVISED 2026-11-16 after the spike (see "Spike results" at the end).** Stripe rejects the creation
> of v1 Standard accounts for a new platform, so the decision below is replaced by **Accounts v2**
> (`dashboard: full`, `merchant` configuration, fees and losses collected by Stripe). The reasoning
> about the studio being the merchant with a full Dashboard still holds. The text below is kept as
> the original reasoning.

- **Decision**: a **Standard** connected account (v1 API, `type=standard`), created by
  MusicStudio and onboarded on Stripe's hosted pages. All account calls live in `gateway.py`, so
  moving to the newer Accounts v2 API (`dashboard: full`, `merchant` configuration) later touches
  that one file and the event attribution only.
- **Why**: the studio is the merchant and gets the full Stripe Dashboard (balances, payouts,
  refunds, disputes), which is exactly the owner's intent. Sources agree that Standard accounts
  cost the platform nothing per account (Express and Custom carry monthly and payout fees) **to
  verify on Stripe's pricing page**. Events carry a top-level `account` field, which makes studio
  attribution trivial.
- **Risk**: Stripe's current docs call Standard, Express and Custom "legacy" and recommend Accounts
  v2 for a new platform. They do not say v1 Standard stops working. The spike checks that a new
  platform can still create one in the sandbox; if not, v2 replaces it inside the gateway.
- **Rejected**: Express and Custom (per-account fees, the platform takes on more responsibility and
  would need to hold more data); Accounts v2 first (newer, thin-event model, less documentation to
  study from, more code for the same result).

## R2 - Which charge type

- **Decision**: **direct charges**: the Checkout Session is created *on the connected account*
  (`Stripe-Account` header). No `application_fee_amount`, no `on_behalf_of`, no transfer.
- **Why**: the money is created on the studio's account and never touches the platform's balance;
  Stripe fees, refunds and disputes are the studio's (documented behaviour of direct charges). It is
  the only charge type that makes "the platform never holds money" literally true.
- **Rejected**: destination charges and separate transfers (the money first lands on the platform's
  account, which is the thing this phase removes).

## R3 - Onboarding

- **Decision**: Stripe-hosted onboarding through an **Account Link** (return and refresh URLs point
  to a portal page). On return the portal asks the backend to re-read the account, and the
  `account.updated` event keeps the state fresh afterwards. The studio opens Stripe's own
  Dashboard to manage the account; there is no login-link API for Standard accounts, only the
  public Dashboard address (the test-mode one while in test mode).
- **Privacy**: the owner's email is **not** sent to Stripe; the owner types it on Stripe's page.
  The only data we send is `metadata.studio_id`. We store the account id and a derived state.

## R4 - Webhook endpoints

- **Decision**: a **second endpoint**, `/api/v1/webhooks/stripe-connect/`, with its own signing
  secret (`STRIPE_CONNECT_WEBHOOK_SECRET`), registered in the Stripe Dashboard as "Connected
  accounts". The existing endpoint keeps working for events of the platform's own account. Both
  call the same store-then-process path (ADR-014) and the same IP allowlist (ADR-021).
- **Why**: events of connected accounts are delivered only to an endpoint of the "connected
  accounts" kind, and each endpoint has its own secret. One shared route would need two secrets
  tried in turn; two routes are clearer and each test is simple.
- Events with `livemode: true` are stored and ignored (test mode only, FR-029).

## R5 - Events and how they map

- `checkout.session.completed`, `.async_payment_succeeded`, `.async_payment_failed`, `.expired`:
  as today, plus the attribution to the studio account named by the event.
- **Refunds**: `refund.created` and `refund.updated`, acted on only when the refund's status is
  `succeeded`; the refund id makes the reversal idempotent. `charge.refunded` is *not* used because
  recent API versions no longer embed the list of refunds in the charge. **To verify** in the
  sandbox that the refund event arrives on the connected-accounts endpoint with `account` set.
- **Disputes**: `charge.dispute.created` records an open dispute on the payment;
  `charge.dispute.closed` with status `lost` creates the reversal, `won` closes the dispute with no
  reversal. Between the two, Stripe has already withdrawn the money from the studio; the register
  shows "paid" with an "under dispute" mark, which is true to the facts.
- **Account state**: `account.updated` (state derivation in R7) and
  `account.application.deauthorized` (the studio disconnected MusicStudio from its Stripe account).
- Events we do not handle are stored and ignored, as today.

## R6 - Partial refunds in the register

- **Problem**: phase 8 says one reversal per payment, repeating the full amount
  (`reversal_of` is one-to-one). A partial refund, or two refunds in a row, does not fit.
- **Decision**: `reversal_of` becomes a **foreign key** (a payment can have several reversal rows).
  A new column `cause` (`manual`, `refund`, `dispute`) and a nullable unique `provider_ref` (the
  Stripe refund or dispute id) are added.
  - A **manual** reversal stays full and unique: a partial unique constraint on `reversal_of` where
    `cause = 'manual'` keeps the guarantee of phase 8 at database level.
  - A **provider** reversal carries the refunded amount. The sum of the reversals of a payment can
    never exceed its amount; the service enforces it under a row lock (the same pattern as phase 8
    and as receipt numbers), and `provider_ref` makes a repeated notification a no-op.
  - A payment counts as **reversed** (package open again, out of "effective paid") only when its
    reversals add up to its amount. A partial refund lowers the net total and leaves the package
    paid: the lessons were still given.
- **Cost**: about ten places use `payment.reversal` or `reversal__isnull`: selectors, serializers,
  the student selectors, the register summary and the factories. They switch to a small selector
  that annotates the reversed amount. Existing rows need no data change (`cause` defaults to
  `manual`).
- **Rejected**: leaving partial refunds out and only flagging them (the register would show money
  the studio no longer has, which the spec forbids); modelling a partial refund as a full reversal
  plus a new paid row (it invents a payment that never happened); a separate "refunds" table (the
  totals and exports would have two sources to add up).

## R7 - Account state

- A single `state` derived from what Stripe reports, never from what MusicStudio guesses:
  `not_started` (no account row), `in_progress` (details not submitted), `information_needed`
  (submitted, requirements due), `active` (charges enabled), `restricted` (Stripe disabled the
  account), `disconnected` (deauthorized). Only `active` allows paying online.
- Stored: account id, state, last change. Not stored: requirements, documents, bank data,
  business name.

## R8 - Payment methods and PayPal

- Checkout keeps **no `payment_method_types`**: the studio chooses its methods in its own Stripe
  Dashboard and Stripe picks the best for each payer (this is how phase 3 works).
- **PayPal is not promised.** Stripe lists PayPal for connected accounts in Italy, but the page
  marks it as available by invitation, and one developer report (not Stripe documentation)
  says Stripe rejected PayPal on direct charges in test mode. **To verify** in the sandbox. Cards,
  Apple Pay, Google Pay and bank debits are the sure ground.

## R9 - The earlier platform-account path

- The endpoint `POST /packages/{id}/checkout/` **stays at the same address**. It now creates the
  session on the studio's account, and answers `409 online_payments_not_available` when the studio
  has no active account.
- No client calls it today: the portal has no pay button and the mobile app only carries the
  generated types. So nothing breaks; the portal gets the button in this phase and the mobile app
  gets a follow-up note (as in phase 8).
- Checkout attempts that exist from phase 3 (test mode, no account id) stay in the table; the
  reconciliation reads them without the account header.

## R10 - Personal data in stored events

- Today `WebhookEvent.payload` stores the whole event, which for a Checkout session includes the
  payer's email and name. Connect events add billing details. Principle X says logs and error
  reports hold identifiers only; a database column of raw events is a copy of personal data that
  nobody can export or erase.
- **Decision**: store a **scrubbed** payload (a whitelist: ids, status, amounts, currency,
  payment intent, charge, refund and dispute ids, account), and delete processed events older than
  90 days with the existing nightly retention job. The scrub is one function with a test that feeds
  it a real-shaped event full of personal data.

## R11 - Reconciliation

- The hourly reconciliation keeps working and now passes the stored account id of each attempt.
  A refund or a dispute missed by the webhook is not reconciled automatically (the studio sees
  them on its Stripe Dashboard); the register for the day is wrong until the event is replayed.
  Stripe retries a failed delivery for days, and the event store makes a replay safe. A periodic
  refund check is not worth its code now.

## R12 - Spike to run first (needs the owner's sandbox)

1. A new platform can create a Standard account through the API (R1), and its pricing is zero for
   the platform (R1).
2. A Connect webhook endpoint receives `checkout.session.completed`, `refund.*`, `charge.dispute.*`
   and `account.updated` with the `account` field set (R4, R5).
3. Whether PayPal appears in Checkout for a test connected account (R8).
4. Whether test mode needs the platform profile completed before Connect works.
5. The exact shape of a refund and a dispute event, saved as fixtures for the tests.

If item 1 fails, R1 falls back to Accounts v2 inside `gateway.py`; nothing else in the plan
changes.

## Spike results (2026-11-16, Stripe sandbox of the owner, SDK `stripe` 16.1.0)

Run by Claude with the owner's sandbox key read from a file outside the repo; only identifiers'
last characters and field names were printed. One test connected account (id ending `5Jb5`) was
left in the sandbox.

- **Key and platform**: a test key (`sk_test_`), the account is Italian, Connect is active with the
  "Platform" business model ("merchants collect payments directly"), zero connected accounts at
  the start. The sandbox already had RevenueCat connected, no webhook endpoint, and a restricted key
  that is not ours.
- **R12 item 1, v1 Standard: FAILS.** `accounts.create(type="standard", country="IT")` returns
  `InvalidRequestError`: "Stripe no longer recommends Accounts v1 for new Connect integrations.
  Create connected accounts with POST /v2/core/accounts instead." So the fallback of R1 applies.
- **Accounts v2: WORKS.** `client.v2.core.accounts.create` with `identity.country=IT`,
  `dashboard="full"`, `configuration.merchant.capabilities.card_payments.requested=true` and
  `defaults.responsibilities.fees_collector="stripe"`, `losses_collector="stripe"` creates the
  account (`applied_configurations=["merchant"]`, `dashboard="full"`). Before onboarding,
  `configuration.merchant.capabilities.card_payments.status` is `restricted` and
  `requirements.entries` holds 19 open items.
- **Onboarding link (v2)**: `client.v2.core.account_links.create` with
  `use_case={"type":"account_onboarding","account_onboarding":{"return_url":...,"refresh_url":...}}`
  works and returns `url` (host `connect.stripe.com`) and `expires_at`. The field `configurations`
  inside `account_onboarding` is rejected ("Unknown field").
- **SDK**: 16.1.0 already carries `client.v2.core.accounts` and `account_links`; no upgrade needed.
- **Platform cost (R1)**: Stripe's public Connect pricing page (Italian) says that a platform that
  lets Stripe bill the connected accounts' fees has "no additional fees for the account, payout
  volume, tax reporting or single payouts"; the model where the platform handles the fees costs
  EUR 2 per active account per month, 0.25% + EUR 0.10 per payout and more. The page does not say
  that `fees_collector="stripe"` is exactly the first model: **to confirm in the Dashboard**
  (Connect settings / pricing) before live mode.
- **Account state (R7), consequence**: the state comes from the v2 account: the merchant
  capability status (`active`, `restricted`, ...) and `requirements`. `details_submitted` and
  `charges_enabled` do not exist in v2.
- **Webhooks (R4, R5), consequence**: v2 account events are "thin events" delivered to an event
  destination, a different mechanism from v1 webhook endpoints. To keep this phase simple the
  account state is refreshed **on demand** (when the owner returns from Stripe, when the settings
  page opens while the account is not active, and by an hourly task for accounts not active yet),
  not through v2 events. Payment, refund and dispute events stay v1 events on a connected-accounts
  endpoint. Listening to the v2 account events is a FUTURO.
- **A connected account cannot be completed through the API (tried, refused).** With the Dashboard
  full or none and the losses collected by Stripe (the only combination allowed for a new platform;
  `losses_collector="application"` is refused, `dashboard="express"` is "not supported"), Stripe owns
  the collection of requirements and answers "You cannot accept the Terms of Service on behalf of
  accounts where requirement collection is owned by Stripe." So the studio's owner always accepts
  the terms on Stripe's hosted page: good for privacy (we collect nothing), and it means the
  sandbox run needs a human to finish hosted onboarding with test data (SMS code `000-000`, date of
  birth `1901-01-01`, address line `address_full_match` with a real city and postcode, personal id
  `000000000`, business URL `https://accessible.stripe.com`).
- **Still open**: R12 item 2 (do the v1 events arrive with the `account` field), item 3 (PayPal) and
  the direct charge itself: they need a connected account that finished onboarding with test data,
  which the owner completes on Stripe's hosted page.

## R13 - Testing without Stripe

- `tests/fakes.py` already replaces the gateway. It grows the account functions and a per-account
  session store. Event payloads for the processing tests are the real-shaped fixtures of R12, so
  the tests exercise real structures even though no network is used.
- One end-to-end run against the sandbox (onboarding, payment, refund, dispute) is recorded in the
  study documentation (SC-009).
