# Data Model: Studio Cash Register, Payment Instructions and Receipts

Everything lives in `backend/apps/payments`. Existing rows stay valid and unchanged (FR-034):
every new column on `Payment` is nullable or has a default, and no data migration is needed.

## Payment (existing, extended)

| Field | Type | Notes |
|---|---|---|
| `status` | choices | adds `reversal` to `paid`, `pending`, `overdue` |
| `reversal_of` | OneToOne to `self`, null, `PROTECT`, `related_name="reversal"` | set only on a reversal row; the link points to the original |
| `reason` | `EncryptedTextField`, blank | why a reversal was made; free text, encrypted (Principle X); at most 200 characters, enforced in the serializer |
| `recorded_by` | FK to user, null, `SET_NULL` | who created the row; null for old rows and for the card webhook |

New constraints and index:

- `payment_reversal_link_matches_status`: `status = 'reversal'` if and only if `reversal_of` is not
  null. A reversal without link, or a link on a non-reversal, cannot exist.
- `payment_reversal_amount_positive`: a reversal row has `amount > 0` (it repeats the original's
  amount; the sign is carried by the status).
- Index on `date`, for the period filters (research R4).

Derived, never stored:

- **reversed** (an original): it has a row in `reversal`. Exposed as a read-only boolean.
- **display status** for the register: `reversed` when reversed, otherwise the stored status.

### Rules (enforced in `services.py`; the link and constraints are enforced by the database)

- A row with status `paid` or `reversal` is final: no edit of amount, date, method, student,
  package or status, and no delete (409 `payment_final`).
- `pending` and `overdue` rows follow the existing transition table
  (`pending → paid | overdue`, `overdue → paid`) and can be deleted; deletion is audited first.
- `reverse_payment(original, reason, actor)`:
  1. lock the original (`select_for_update`);
  2. refuse unless `status = paid`, and refuse if it already has a reversal or is itself a reversal;
  3. create the reversal row: same student, package, amount, method; `date = localdate()`;
     `status = reversal`; `reversal_of = original`; `reason`; `recorded_by = actor`;
  4. write the audit entry `payment.reverse`.
  The unique `reversal_of` makes a second concurrent reversal fail even if step 2 raced.
- The package of a reversed original is open again when no other paid, non-reversed entry covers it.
  The lessons already completed are not touched.

### State picture

```text
pending ──► paid ──(reverse)──► [paid + reversed]   (original untouched, gets a reversal row)
   │          ▲                       │
   └─► overdue ┘                      └── reversal row (status reversal, final, cannot be reversed)
```

### Totals for a period (from–to, inclusive, local dates), per studio scope

```text
received = sum(amount where status = paid        and date in period)
reversed = sum(amount where status = reversal    and date in period)
net      = received − reversed
```

Per payment method, the same three sums grouped by `method`. Pending and overdue rows are listed
but never counted. A November payment reversed on 3 December adds to November's `received` and to
December's `reversed`.

## PaymentInstructions (new)

One row per studio.

| Field | Type | Notes |
|---|---|---|
| `studio` | OneToOne to `studios.Studio`, `CASCADE` | the key; a studio has at most one |
| `account_holder` | `EncryptedTextField` | required when an IBAN is given |
| `iban` | `EncryptedTextField` | normalised (no spaces, uppercase), format and mod-97 checked |
| `bank_name` | `CharField(100)`, blank | |
| `note` | `CharField(200)`, blank | for example what to write as the transfer reason |
| `links` | `JSONField`, default list | up to 5 of `{label (1–40), url (https, up to 500)}` |
| `updated_by` | FK to user, null, `SET_NULL` | |
| `updated_at` | datetime, auto | |

Validation lives in the serializer plus `iban.py`. Saving is `services.save_instructions(studio,
actor, data)`; it writes the audit entry `instructions.change` with only the names of the fields
that changed, never their values. Deleting the instructions is a `PUT` with every field empty, or
the studio owner's account erasure.

## Receipt (new)

At most one per payment.

| Field | Type | Notes |
|---|---|---|
| `payment` | OneToOne to `Payment`, `CASCADE` | cascade only matters for the 10-year retention job |
| `studio` | FK to `studios.Studio`, `PROTECT` | stored so the number can be unique per studio |
| `year` | `PositiveSmallIntegerField` | local year of first generation |
| `sequence` | `PositiveIntegerField` | 1, 2, 3… within `(studio, year)` |
| `language` | choices `it`, `en` | chosen at first generation |
| `issued_by` | FK to user, null, `SET_NULL` | |
| `issued_at` | datetime, auto | |

Constraints: unique `(studio, year, sequence)`; the one-to-one on `payment` makes a second receipt
for the same payment impossible. The visible number is `f"{year}-{sequence:04d}"`, computed, not
stored.

Rules in `services.issue_receipt(payment, language, actor)`:

- only a `paid` payment (not a `reversal`, not `pending`/`overdue`);
- idempotent: if a receipt exists, return it (same number, same language);
- otherwise lock the studio row, take `max(sequence) + 1` for the current local year, insert;
- audit entry `receipt.issue`;
- a payment that is reversed keeps its receipt, and the PDF carries a "cancelled" mark computed from
  the reversal link at render time.

The PDF shows: studio name, student name, amount, date, method, receipt number, the sentence
"not a tax document" (IT and EN), and the "cancelled" mark when reversed. Nothing else (FR-029).
After an erasure request the student's name is already the anonymised label, so the receipt shows it.

## Scoping

`Receipt` gets its own `TenantPaths` in `apps/common/scoping.py`:

```text
RECEIPT_PATHS = TenantPaths(
    studio="payment__student__studio",
    teacher="payment__student__teacher",
    parent="payment__student__parent_accounts",
    student="payment__student",
)
```

`PaymentInstructions` is never listed by id: owners and teachers get their own studio's row through
the tenant context; parents get the open-package list built from their visible students.

## Audit actions added

`payment.reverse`, `payment.delete`, `register.export`, `instructions.change`, `receipt.issue`.
Metadata uses only short non-personal values: method, amount as text, period as two ISO dates,
row count, names of changed fields.

## Indexes and query shape

- Register list and summary: scoped payments (join to student for the tenant filter) filtered by
  `date`; one aggregate query for the summary; the list is paginated with `select_related("student",
  "reversal")` so the count of queries does not grow with the page.
- Receipt list: `select_related("payment__student")`.
- Parent open packages: one query for packages without a paid, non-reversed entry, one for the
  distinct studios' instructions.
