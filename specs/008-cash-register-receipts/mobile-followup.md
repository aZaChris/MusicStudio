# Mobile follow-up: cash register, payment instructions, receipts (phase 008)

The app on branch `mobile` reads the contract from `main` (`backend/openapi.yaml`). This phase
changes it in an additive way plus one deliberate tightening. Nothing here was run against the app:
it is a reading of the code (`src/app/(teacher)/payments.tsx`, `src/app/(parent)/portal.tsx`) and of
the generated types.

## What changes for the app

1. **`status` of a payment gains `reversal`.** A correction is a new entry with that status. Any
   badge or filter that switches on `paid`, `pending`, `overdue` must treat `reversal` (and an
   original that reads `reversed: true`) as history, not as money to collect. Today the teacher
   payments screen counts "to collect" as "not paid": a reversal row would be counted. This is the
   one change that can make the app show a wrong number, so check it first.
2. **New read-only fields on each payment**: `reversed` (bool), `reversal_of`, `reversal_id`,
   `receipt_number`, and, for teachers and owners only, `reason` and `recorded_by`. Parents never
   receive the last two.
3. **Update and delete of a paid entry now answer 409 `payment_final`.** The app only lists and
   creates payments (`registerPayment`); its generated types still contain update and delete, but
   no screen calls them. If one is added, reverse instead.
4. **`GET payments/` accepts `date_from`, `date_to`, `method`.** Existing calls keep working.

## What the app could add later

- Teacher: reverse a paid entry (`POST payments/{id}/reverse/` with a reason; always
  `refund: false`), the period summary (`GET payments/register/summary/`), issue and download
  a receipt (`POST payments/{id}/receipt/`, `GET receipts/{id}/pdf/`). Exports (CSV, PDF) are a
  web feature for the accountant.
- Parent: `GET payment-instructions/open/` (instructions with `student_ids`, shown beside the
  child's open package, with the statement that payment happens outside the app) and
  `GET receipts/?student=` with downloads.
- Owner: edit the instructions (`PUT payment-instructions/`), teachers read.

## Screens that show a payment status

- `src/app/(teacher)/payments.tsx` (list, "to collect" count, status chip)
- `src/app/(parent)/portal.tsx` (the child's payments)
- the student roster's `payment_status` (it now ignores reversals and reversed entries, so it can
  also be `null`, which it could before)

When the app is regenerated from the new contract (`contract:check`), TypeScript will point at the
places that switch on the status enum.
