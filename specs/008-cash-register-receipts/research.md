# Research: Studio Cash Register, Payment Instructions and Receipts

All unknowns from the plan are resolved here. Each entry: decision, why, what was rejected.
No `NEEDS CLARIFICATION` is left.

## R1. How a paid entry is corrected

**Decision**: a reversal is a new `Payment` row with `status = reversal`, `reversal_of` pointing
to the original (a one-to-one, so unique), the same student, package, amount and method, the
date of the day it is made, an encrypted `reason` and `recorded_by`. The original row is never
written again. "Reversed" is derived: the original has a reversal.

**Why**: the register must show the original untouched (SC-001) and a closed month must never
change (FR-003). If the original were updated to "reversed" its `updated_at` would move and any
total computed by status would change retroactively. A unique link makes "at most once" and "two
teachers at once, one reversal" (FR-004, FR-009) a database guarantee: the second insert fails on
the unique constraint, and the service also locks the original row so the loser gets a clean 409.

**Rejected**:
- *Mark the original `reversed` and add a counter-entry*: mutates history and breaks monthly totals.
- *Negative amounts on the reversal*: a `CheckConstraint` on positive amounts is simpler to reason
  about, and the sign is a property of the status; totals subtract reversals explicitly.
- *A separate `Reversal` table*: a second place to query for every list and total, with no gain.
- *Soft delete flag*: hides the entry instead of showing the correction.

## R2. IBAN validation

**Decision**: a small `iban.py` with the standard library: strip spaces, uppercase, check
`^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$`, then the mod-97 checksum (move four characters to the end,
letters to numbers, integer modulo 97 must be 1). No per-country length table; Italian IBANs are
27 characters and the checksum already catches almost every typing mistake.

**Why**: about fifteen lines and a test with known valid and invalid numbers; the same approach as
TOTP in ADR-029 (standard library over a dependency for something small and well specified).

**Rejected**: `schwifty` or `python-stdnum` (a dependency for fifteen lines); a country length table
(more data to maintain, little extra safety for a free-text field the teacher can verify).

## R3. CSV for the accountant

**Decision**: Python `csv` module, UTF-8 with a BOM, semicolon separator, decimal point,
`\r\n` line ends. Text cells (student name, reason, package label) are neutralised: a value that
starts with `=`, `+`, `-`, `@`, tab or carriage return gets a leading apostrophe. Numeric columns
are written from `Decimal`, never from user text, so a legitimate `-40.00` is not touched.

**Why**: Excel with an Italian locale splits columns on `;` and needs the BOM to read accents. The
neutralisation follows the OWASP CSV injection guidance (FR-015).

**Debatable**: a comma separator is the international default; Italian accountants are the first
audience, so the semicolon wins. If a studio asks for a comma, a query parameter can be added later.

**Rejected**: `.xlsx` (new dependency, not asked for); quoting every cell (does not stop formulas).

## R4. Totals and period rules

**Decision**: one query with conditional aggregates over the scoped queryset, filtered by
`date` between the two local dates:
received = `Sum(amount, filter=status=paid)`, reversed = `Sum(amount, filter=status=reversal)`,
net = received − reversed, grouped by method for the per-method lines. Pending and overdue rows
are listed in the register but never counted (FR-011). `Payment.date` is a `DateField` already in
local terms (the teacher enters it; the webhook uses `timezone.localdate()`), and the reversal date
is `timezone.localdate()`, so Europe/Rome is respected without datetime arithmetic (FR-012).
The period of an export is at most 366 days; the summary and list accept any period.

**Why**: a net per period that equals a hand calculation (SC-002) is easiest to prove when it is
one SQL expression; a November payment reversed in December stays in November's received and
December's reversed, which is exactly the accounting the spec asks for.

**Index**: add `Index(fields=["date"])`; the scope join to the student does the tenant filtering and
the planner picks the date range first. The 2,000-entries-in-3-seconds goal is checked with a
seeded test (`seed_loadtest` data) in the tasks.

## R5. What "open package" and "payment status" mean after reversals

**Decision**: one rule, written once as a selector and a queryset helper:
a package is **paid** when it has a `paid` entry that has no reversal; **open** otherwise.
`package_is_paid` (used by checkout), the roster's `latest_payment_status` subquery and the new
parent selector all use it. The roster's latest status looks at rows that are neither reversals nor
reversed, so reversing the only paid entry makes the student's status fall back to the earlier one
(or none), not to a confusing `reversal`.

**Why**: FR-005 says a reversed entry makes its package payable again; the checkout guard must agree
or a parent could be told "already paid" for money that was reversed.

## R6. Making paid entries final

**Decision**: in `services.update_payment` and a new `delete_payment`: a row whose status is `paid`
or `reversal` raises `PaymentFinal` (a `DomainConflict`, HTTP 409, code `payment_final`). Pending and
overdue rows are edited as today; deleting them writes an audit entry first. The viewset calls the
services for update and destroy.

**Why**: this matches the service-layer rule (Principle V) and the existing transition table
(`paid` has no way out). A 409 with a code lets the clients explain "use a reversal instead".

**Known limit, stated plainly**: `QuerySet.update()` and `QuerySet.delete()` skip model methods, so a
developer could bypass the rule. A database trigger would close that, but adds migration and
operational weight for little gain in a single-codebase product. A test walks the code paths that
write payments and fails if a new one appears (the same compromise as the audit signals in ADR-017).
The 10-year retention job deliberately deletes in bulk; ADR-034 names it as the only exception.

**Rejected**: overriding `Payment.save/delete` (costs a query to know the stored status, still
bypassable); trigger (see above).

## R7. Receipt numbers without gaps or repeats

**Decision**: `issue_receipt` runs in a transaction: lock the studio row with `select_for_update`
(the pattern `add_teacher_to_studio` already uses), read `max(sequence)` of that studio and the
current local year, insert `Receipt(sequence=max+1, year=…)`. The number is `YYYY-NNNN`. Unique
constraints on `(studio, year, sequence)` and on `payment` are the safety net. If the transaction
rolls back, the number is not consumed.

**Why**: SC-007 wants twenty simultaneous requests to give twenty gapless numbers; a lock on one
row per studio serialises only that studio's receipts. Using `max` and not `count` keeps numbers
unique even if old receipts disappear with the retention job.

**Rejected**: a PostgreSQL sequence per studio (gaps on rollback, one object per studio to manage);
an `AutoField` per studio-year counter table (one more table for what a lock already gives);
`select max` without a lock (races).

**Content on regeneration**: the receipt stores number, language, who and when. The PDF is rendered
on demand from the live payment, student and studio names. The same input gives the same PDF; if
the studio or the student is renamed, the next rendering shows the new name. That is accepted: a
stored snapshot of a name would outlive an erasure request (FR-031).

## R8. Payment instructions for parents

**Decision**: one endpoint for the parent portal, `GET /api/v1/payment-instructions/open/`, returns a
list of instructions, one per studio that has at least one open package among the caller's visible
students. The SPA matches a package to its instructions by the student's studio (already in the
student payload). Owners and teachers use `GET`/`PUT /api/v1/payment-instructions/`, always for
their own studio, never by id.

**Why**: putting instructions inside each package would repeat them and run a query per package
(Principle III). One list gives a constant query count and nothing for students with no open package
(FR-021).

**Storage**: `PaymentInstructions` is one row per studio (one-to-one). `account_holder` and `iban`
are `EncryptedTextField` (FR-023). `bank_name` and `note` are short plain text (a note such as "write
the student's name in the reason" is not a secret). Links are a JSON list of `{label, url}` validated
in the serializer: at most five, `https` only, label 1–40 characters, URL up to 500. A list in JSON
beats a child table here: always read and written as a whole, never queried.

**Rejected**: per-package instructions (duplication); per-teacher instructions (out of scope in the
spec); storing the IBAN in plain text (FR-023).

## R9. Impact on the mobile app

**Finding** (branch `mobile`, checked at planning time): the app lists payments and creates them
(`registerPayment` in `src/app/(teacher)/payments.tsx`; its tests mock `POST /payments/`). Its
generated types contain the update and delete operations, but no screen calls them. The web
portal (`frontend/`) likewise only lists and creates.

**Decision**: the new rules are safe for both clients. They are still written in
`contracts/api.md` as a change of mutation rules, and a line is added to the mobile follow-up note
when this feature is implemented. New response fields are additive (`reversed`, `reversal_of`,
`recorded_by`), so the app's reads keep working.

**Caveat**: the `status` enum gains `reversal`. A client that switches on every known status value
should treat an unknown one gracefully; the mobile app's payment status badge is the place to check
in the follow-up. This is a reading of the code, not a run of the app.

## R10. PDF library

**Decision**: `reportlab` (BSD). It writes PDFs from Python with tables and the built-in Helvetica
font, which covers Italian accents and the euro sign through WinAnsi encoding. Wheels exist for
Linux and macOS, and it needs no system library, so the slim Docker image stays as it is.

**Why**: the two documents are simple (a title, a few lines, a totals table); no HTML rendering is
needed.

**Rejected**: `WeasyPrint` (needs Pango and Cairo system packages in the image); `fpdf2` (fine and
LGPL; kept as the fallback, see plan); headless browser (heavy, a security surface); client-side
PDF generation (the register must be produced by the server so the audit log can record it).

**Check in T001**: `uv add reportlab`, render a sample with `à è ì ò ù €`, build the image.

## R11. Who can do what

**Decision**:

| Action | Owner | Teacher | Parent / adult student |
|---|---|---|---|
| See register, summary, export | whole studio | own students | no (403) |
| Reverse, delete pending, issue receipt | whole studio | own students | no |
| Read instructions (own studio) | yes | yes | only through the open-package list |
| Change instructions | yes | no (403) | no |
| Download an issued receipt | yes | yes | own student only |

Role checks are permission classes (Principle I). The register endpoints use a strict
teacher-or-owner class; `IsTeacherOrStudioOwner` allows reads for every authenticated user, which
is right for the existing list used by the parent portal but wrong here, so the existing
`IsTeacherOrOwnerRole` (today in `accounts`) is moved to `common/permissions.py` and reused.
For the existing `GET /payments/` that parents already use, the serializer hides `reason` and
`recorded_by` from parents and adult students (the reason is encrypted free text).

## R12. Audit, logs and error reports

**Decision**: new audit actions: `payment.reverse`, `payment.delete`, `register.export`,
`instructions.change`, `receipt.issue`. Metadata stays within the existing safe types (a method, an
amount as text, a period as two ISO dates, a count). Bank details never enter metadata
(FR-023, SC-008). Sentry's scrubber (`before_send`) gets `/payment-instructions/` in its list of
sensitive paths, so the request body of a failed save is never sent. A test submits an IBAN in a
failing request and checks the logs and the captured event.

## R13. Downloads in the SPA

**Decision**: the portal fetches CSV and PDF with its authenticated client (the access token is in
memory, ADR-023), turns the response into a `Blob` and triggers the download. No token goes into a
URL and no signed-URL machinery is added.

**Rejected**: `window.open` on an API URL (would need the token in the query string).

## R14. Throttling

**Decision**: a new throttle scope `register_export` (default `20/hour`) on the two exports and on
receipt PDFs, the heaviest reads. Other endpoints keep the default user rate.

## R15. Owner data export and erasure (FR-023)

**Finding**: today `ExportView` is limited to parents and adult students, and `students_of(user)` is
empty for an owner. The spec requires the owner's own export to include the instructions.

**Decision**: allow the studio owner on `ExportView` with a minimal payload: the account block and a
`studio` block (name and the instructions, decrypted). Nothing about students or payments is added
to the owner's export; the studio's books are not personal data of the owner. When an owner erases
their account (already blocked while the studio has students), the instructions row is deleted
before the account is emptied.

## R16. Roadmap bookkeeping

`CLAUDE.md` gets a new row in the roadmap table (phase 8, this feature). The spec noted that
phase 7's text reserved "phase 008" for notes, progress and materials; those stay unplanned and
are not renumbered.
