# Quickstart: validating phase 9

Two parts: the automated checks (no Stripe, always possible) and the run against a **Stripe
sandbox** (needs the owner's account, recorded once for SC-009). Test mode only: never use a live
key.

## 1. Automated (backend)

```bash
cd backend
export DATABASE_URL=postgres://$USER@/musicstudio
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test --noinput
rtk proxy uv run pytest apps/payments            # the exact result matters: use rtk proxy
uv run pytest                                    # whole suite, coverage floor 90%
uv run python manage.py spectacular --settings=config.settings.test --fail-on-warn --file openapi.yaml
```

Expected: green. The payments tests prove, with a fake gateway and real-shaped event fixtures:
cross-studio denial on every new endpoint, one entry per confirmation (replayed 3 times), one
reversal per refund id, the sum of reversals never above the amount (also with 6 real threads),
unknown accounts ignored, scrubbed event payloads, query budgets, and that a studio without an
active account cannot start a payment.

## 2. Automated (portal)

```bash
cd frontend && npm test -- --run && npm run build
```

Expected: the owner's payments settings page, the parent's "Pay online" button and the return
pages pass their tests; types regenerate with no drift from `openapi.yaml`.

## 3. Sandbox run (owner's Stripe account)

Prerequisites: a Stripe **sandbox**, Connect enabled on it, a restricted or secret **test** key in
`STRIPE_API_KEY`, the Stripe CLI logged in, the stack running locally.

1. `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe/` and, in a second terminal,
   `stripe listen --forward-connect-to localhost:8000/api/v1/webhooks/stripe-connect/`; put the two
   printed `whsec_...` values in `STRIPE_WEBHOOK_SECRET` and `STRIPE_CONNECT_WEBHOOK_SECRET`.
2. As a studio owner open the payments settings, start onboarding, fill Stripe's test data (the
   test onboarding offers a shortcut) and return: the state reads `active`.
3. As a parent linked to a student with an open package, press "Pay online", pay with
   `4242 4242 4242 4242`: the package is paid, the register has one `Online (Stripe)` entry, and the
   Stripe sandbox shows the charge **on the connected account**, not on the platform.
4. Refund it from the connected account's Dashboard (or
   `stripe refunds create --payment-intent <pi_...> --stripe-account <acct_...>`): one reversal with
   the cause `refund`, package open again, net total zero. Try a partial refund on a second payment.
5. Pay again with the dispute test card `4000 0000 0000 0259`; the entry shows "under dispute";
   close the dispute as lost in the Dashboard: a reversal with the cause `dispute`.
6. If PayPal appears in Checkout for the test account, note it; if not, note that too (research R8).
7. Record the date, results and surprises in `docs/learning/concetti/` (the phase's concept file)
   and keep the real event payloads as the test fixtures (scrubbed).

## 4. Phase 8 walk still holds

Run `specs/008-cash-register-receipts/quickstart.md` for a studio with **no** connected account:
nothing changes (SC-008).
