# Mobile follow-up: phase 9 (online payments to the studio's own Stripe account)

For branch `mobile`. Nothing here breaks the app: no mobile screen calls the checkout today, and the
new fields are additions. This is what to do when the mobile app catches up with `main`.

The whole feature is **off by default** (`ONLINE_PAYMENTS_ENABLED=false`), so on a server where it is
off the new routes answer 404 and `can_pay_online` is always `false`.

## Contract changes (see `backend/openapi.yaml`)

- `Package.can_pay_online` (boolean, read-only): the studio's Stripe account is active and the package
  is still to be paid. It is also on `Student.active_package`. Show a "Pay online" button only when true.
- `POST /packages/{id}/checkout/`: same address and response, but now creates the payment on the
  **studio's own** account. New answers: `409 online_payments_not_available` (no active account, or the
  feature is off) and `409 package_already_paid`. Open the returned `url` in the system browser; do not
  claim success when the user comes back: the register is updated by Stripe's own confirmation.
- `Payment` (read): new `reversed_amount` (string decimal, sum of its reversals), `under_dispute`
  (boolean) and `cause` (`manual | refund | dispute`, meaningful on reversal rows).
- New routes for the studio owner and teachers (`/payment-account/`, `/onboarding/`, `/refresh/`,
  `/restart/`): the app only needs them if it grows an owner area.

## Semantics to respect

- A payment is **reversed** only when `reversed_amount == amount`. A partial refund lowers the net total
  and leaves the package paid; do not show a partly refunded payment as cancelled.
- A reversal row can now come from Stripe (`cause = refund | dispute`), not only from the teacher.
  Wherever the app counts "unpaid" or "to collect" (phase 8 note), treat refunds and disputes like
  reversals: a fully reversed payment is open again.
- A manual reversal is only possible while the payment has no reversal at all (`409 already_reversed`).

## Screens to check

Any screen that shows a payment status badge, a payment list, a package "paid / to pay" state or a count
of unpaid packages (parent home, student detail, payments list).
