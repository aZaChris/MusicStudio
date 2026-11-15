# API Contract: Cash Register, Payment Instructions and Receipts (Phase 008)

All under `/api/v1/`. The machine-readable contract is `backend/openapi.yaml`, regenerated in the
same change. Errors use the existing envelope (`{"detail", "code"}` for domain errors, field
errors for validation). Out-of-scope objects answer **404**, never 403 (Principle I). Dates are
local dates `YYYY-MM-DD` (Europe/Rome). Amounts are decimal strings with two digits.

## Change of mutation rules on `payments/` (read this first)

This is a deliberate contract change (FR-034).

| Request | Before | Now |
|---|---|---|
| `PATCH`/`PUT payments/{id}/` on `pending` or `overdue` | allowed | unchanged |
| `PATCH`/`PUT payments/{id}/` on `paid` or `reversal` | allowed (any field of a paid entry) | **409** `payment_final` |
| `DELETE payments/{id}/` on `pending` or `overdue` | allowed | unchanged; written to the audit log |
| `DELETE payments/{id}/` on `paid` or `reversal` | allowed | **409** `payment_final` |
| `status` value set | `paid`, `pending`, `overdue` | adds `reversal` (never sent by clients) |

Impact checked on the clients (research R9): neither the web portal nor the mobile app calls update
or delete on payments. Reads keep working; new fields are additive.

## Payments (changed)

| Method | Path | Notes |
|---|---|---|
| GET | `payments/` | gains filters `date_from`, `date_to` (inclusive) and `method`; existing `status`, `student` stay. New read-only fields on each item: `reversed` (bool), `reversal_of` (id or null), `reversal_id` (id or null), `recorded_by` and `reason` (staff only, hidden from parents and adult students), `receipt_number` (string or null). Paginated, 25 per page. |
| POST | `payments/{id}/reverse/` | teacher/owner in scope. Body `{"reason": "…"}` (1–200 characters). 201 with the reversal entry. 409 `payment_final`-style codes: `not_paid` (the entry is not paid), `already_reversed`, `is_reversal`. 404 out of scope. The response always carries `"refund": false` (the register is corrected, nothing is refunded); the client states this for `card` entries, using the original's method (FR-007). |

`POST payments/` and the card webhook are unchanged. Every created entry now records `recorded_by`
when a user made it.

## Register summary and exports (teacher/owner only; parents and adult students get 403)

| Method | Path | Query | Response |
|---|---|---|---|
| GET | `payments/register/summary/` | `date_from`, `date_to` (default: the current month) | 200 `{period: {from, to}, totals: {received, reversed, net}, by_method: [{method, received, reversed, net}], counts: {paid, pending, overdue, reversal}}`. Empty period: zeros, not an error. |
| GET | `payments/register/export/csv/` | `date_from`, `date_to` required | 200 `text/csv; charset=utf-8` attachment, one row per entry (below). |
| GET | `payments/register/export/pdf/` | `date_from`, `date_to` required | 200 `application/pdf` attachment: studio name, period, totals per method, production date. |

Rules: `date_from <= date_to`; an export period longer than 366 days is **400**
`{"detail": "…", "code": "period_too_long"}`; both exports are throttled (`register_export`, 20 per
hour per user) and write the audit entry `register.export` with the period and row count.

CSV columns, in order: `date`, `receipt_number`, `student`, `method`, `amount` (negative for a
reversal row), `status` (`paid`, `pending`, `overdue`, `reversed`, `reversal`), `reason`,
`reversal_of`, `package`. Separator `;`, UTF-8 with BOM, text cells neutralised against formulas
(research R3).

## Reversal rules at a glance

- Only a `paid` entry can be reversed; once, ever; a reversal cannot be reversed.
- Two simultaneous requests: one 201, the other 409 `already_reversed`.
- The reversal is dated today, never backdated.
- The original stays `paid` and reads `reversed: true`; the package becomes payable again when no
  other paid, non-reversed entry covers it.

## Payment instructions

| Method | Path | Who | Body / Response |
|---|---|---|---|
| GET | `payment-instructions/` | owner, teacher (own studio) | 200 `{account_holder, iban, bank_name, note, links: [{label, url}], updated_at}`; all fields empty if none saved. |
| PUT | `payment-instructions/` | owner only (teacher 403) | Full replacement of the same body. Validation: IBAN format and checksum (`iban` error), holder required when an IBAN is given, at most 5 links, each `https` with a label of 1–40 characters. Empty body clears the instructions. Audit `instructions.change` lists changed field names only. |
| GET | `payment-instructions/open/` | parent, adult student | 200 list of `{studio_id, studio_name, student_ids, account_holder, iban, bank_name, note, links, notice}` (`student_ids`: the caller's students who have an open package in that studio, so the portal shows the details beside the right child only) for each studio that has at least one open package among the caller's visible students; `notice` is the fixed statement that payment happens outside MusicStudio and is not verified. Empty list when there is nothing to pay or nothing saved. |

Anonymous requests: 401. A user of another studio gets only their own studio's data by
construction (there is no id in these paths). The parent portal matches a package to its
instructions by the student's `studio`. Request bodies of `payment-instructions/` are on Sentry's
sensitive-path list and never reach an error report.

## Receipts

| Method | Path | Who | Response |
|---|---|---|---|
| POST | `payments/{id}/receipt/` | teacher/owner in scope | Body `{"language": "it" \| "en"}` (default: the caller's portal language). 201 on first issue, 200 on repeat, same body: `{id, payment, number, language, issued_at, cancelled}`. 409 `not_paid` for a `pending` or `overdue` entry, 409 `is_reversal` for a reversal entry. 404 out of scope. |
| GET | `receipts/` | teacher/owner (scope), parent/adult student (their own students) | Paginated list of issued receipts; filter `student`. Items as above plus `student_name`, `amount`, `date`, `method`. |
| GET | `receipts/{id}/pdf/` | same scope | 200 `application/pdf`; 404 out of scope. The PDF is rendered from live data; a reversed payment's receipt carries a visible "cancelled" mark. Throttled with the exports. |

Receipt number: `YYYY-NNNN`, unique per studio and year, assigned once, never changed or reused.
The PDF states that it is not a tax document, in the receipt's language.

## Privacy (changed)

- `GET privacy/export/` is now also available to the studio owner, with the account block and a
  `studio` block holding the studio name and the decrypted instructions (research R15).
- `POST privacy/erase/` for an owner deletes the studio's instructions before the account is
  emptied (still refused while the studio has students).
- Erased families: names are the existing anonymised label; amounts, dates and receipt numbers
  remain in the register and on receipts.

## Audit actions added

`payment.reverse`, `payment.delete`, `register.export`, `instructions.change`, `receipt.issue`.
They appear in `GET audit/` for the studio owner like the others; the `action` filter lists them.

## Errors introduced

| Code | Status | When |
|---|---|---|
| `payment_final` | 409 | update or delete of a `paid` or `reversal` entry |
| `not_paid` | 409 | reverse or receipt for an entry that is not paid |
| `already_reversed` | 409 | second reversal, also under concurrency |
| `is_reversal` | 409 | reverse or receipt for a reversal entry |
| `period_too_long` | 400 | export period over 366 days |
