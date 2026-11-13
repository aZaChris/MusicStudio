# Feature Specification: Studio Cash Register, Payment Instructions and Receipts

**Feature Branch**: `008-cash-register-receipts`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Studio cash register, payment instructions and non-fiscal receipts
(points 1-3 of the payments roadmap). MusicStudio is a free service: studios are autonomous and
responsible for their own takings and accounting; the platform never holds or moves money and
does not issue tax invoices. (1) Cash register: today a payment can be edited and deleted; make
payment entries traceable so a mistake is corrected by a reversal entry that keeps the original
visible, with who and when recorded; show totals per day, month and payment method; export the
register as CSV and PDF for the studio's accountant, per period. (2) Payment instructions: each
studio can enter how it wants to be paid (bank details and external payment links) and parents
see those instructions for their own student's open packages; parents pay outside the app and the
teacher marks it paid; nothing is verified against a bank. (3) Non-fiscal receipts: a PDF payment
receipt for a recorded payment, clearly labelled as not a tax document, with studio name, student,
amount, date, method and a receipt number unique per studio. Out of scope: Stripe Connect and
automatic card payments, open banking, electronic invoicing and invoicing integrations,
refunds and disputes handling, any payout."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct a mistake without erasing history (Priority: P1)

A teacher recorded a €40 cash payment for the wrong student. Today they would edit or delete
the entry and nothing would show it ever existed. Instead, they reverse the entry: the original
stays in the register marked as reversed, a linked reversal entry records who corrected it, when
and why, and the totals come out right. Then they record the payment again for the right student.

**Why this priority**: a cash register that can be silently rewritten is not trustworthy, for the
teacher or for their accountant. Everything else in this feature (totals, exports, receipts)
reports on this register, so its integrity comes first.

**Independent Test**: record a payment, mark it paid, reverse it with a reason, and check that
the original is still listed (marked reversed), the reversal appears with actor, time and reason,
the net total for the period is zero, and the package it paid is payable again.

**Acceptance Scenarios**:

1. **Given** a paid entry, **When** the teacher reverses it and gives a reason, **Then** the
   original stays visible marked as reversed, a linked reversal entry is created, and both show
   who acted and when.
2. **Given** a paid entry, **When** anyone tries to change its amount, date, method, student or
   package, or to delete it, **Then** the request is refused and nothing changes.
3. **Given** an entry that is still pending or overdue (no money received yet), **When** the
   teacher edits or removes it, **Then** it works as today, and the removal is recorded in the
   audit log.
4. **Given** a reversed entry, **When** someone tries to reverse it again, or to reverse the
   reversal, **Then** the request is refused.
5. **Given** a card payment recorded by the system, **When** the teacher reverses it in the
   register, **Then** the screen states that no money is returned: the register is corrected,
   nothing is refunded.
6. **Given** two teachers reverse the same entry at the same time, **Then** exactly one reversal
   is created.

---

### User Story 2 - See the totals and give them to the accountant (Priority: P1)

At the end of the month, a teacher or studio owner opens the register for a period (a day, a
month or a custom range) and sees every entry with its status, and totals of what was received,
what was reversed and the net, overall and for each payment method. They export the period as a
file for their accountant: a spreadsheet-friendly file with one row per entry, and a printable
document with the totals.

**Why this priority**: it is the other half of "a register": the owner of a studio has to know
what came in, and to hand it to someone else. It needs nothing from the other stories.

**Independent Test**: with entries on several days and methods, open a month, check the totals
per method against a hand calculation, export both formats, and open the spreadsheet file.

**Acceptance Scenarios**:

1. **Given** paid entries by cash, bank transfer, manual entry and card in a month, **When** the
   user opens that month, **Then** they see received, reversed and net totals overall and per
   method, and totals count only paid entries.
2. **Given** a reversal made on 3 December for a payment dated in November, **When** the user
   opens November and December, **Then** November still shows the original payment and December
   shows the reversal: a closed month never changes.
3. **Given** a teacher in a studio with several teachers, **When** they open the register,
   **Then** they see only their own students' entries; the studio owner sees the whole studio.
4. **Given** a period with no entries, **When** the user opens it, **Then** they see an empty
   register with zero totals, not an error.
5. **Given** a chosen period, **When** the user exports, **Then** they get a spreadsheet-friendly
   file with one row per entry, and a printable document with the studio name, the period, the
   entries' totals per method and the date it was produced.
6. **Given** a student name that starts with `=`, `+`, `-` or `@`, **When** the register is
   exported, **Then** opening the file in a spreadsheet never runs it as a formula.

---

### User Story 3 - Tell parents how to pay (Priority: P2)

A studio owner enters how the studio wants to be paid: the account holder's name and IBAN, an
optional bank name and a short note (for example what to write as the transfer reason), and up
to a few external payment links (PayPal, Satispay and similar). A parent opens their portal and,
next to each of their child's open packages, sees how to pay. They pay outside MusicStudio; the
teacher later marks the payment as received. MusicStudio does not check any bank.

**Why this priority**: it removes the most common question teachers get ("where do I send
the money?") and costs nothing in regulation, because no money passes through the product. It is
useful on its own, but less critical than the register's integrity.

**Independent Test**: as a studio owner, enter an IBAN and one link; as a linked parent, see them
beside an open package; as a parent of another studio, see nothing of them.

**Acceptance Scenarios**:

1. **Given** a studio owner (or a teacher who works alone), **When** they enter an account holder
   and an IBAN, **Then** the IBAN is checked for format and checksum, and an invalid one is
   refused with a clear message.
2. **Given** an external payment link, **When** the owner saves it, **Then** only secure web
   addresses (`https`) are accepted, each with a short label, and no more than a few per studio.
3. **Given** instructions saved by the owner, **When** a parent linked to a student of that studio
   opens the portal, **Then** they see the instructions beside each open (unpaid) package of
   that student, with a plain statement that payment happens outside MusicStudio and is not
   verified by it.
4. **Given** a student with no open packages, **When** the parent opens the portal, **Then** no
   payment instructions are shown.
5. **Given** a studio with no instructions saved, **When** a parent opens the portal, **Then**
   nothing about payment instructions is shown and nothing breaks.
6. **Given** a user of another studio, an anonymous visitor or the studio's own teachers,
   **When** they request the instructions, **Then** other studios' and anonymous requests get
   "not found", and teachers of the studio can read but not change them.
7. **Given** any change to the instructions, **Then** it is recorded in the audit log with who
   and when, without storing the bank details in the log.

---

### User Story 4 - Give the parent a receipt (Priority: P3)

After recording a payment, the teacher produces a PDF receipt for it. The receipt says
clearly that it is **not a tax document**, names the studio and the student, and shows the amount,
the date, the payment method and a receipt number that is unique within the studio. The parent can
download receipts already issued for their own child from their portal.

**Why this priority**: it is useful for parents (proof of payment) and closes the loop, but it
depends on the register being right and nothing else needs it.

**Independent Test**: generate a receipt for a paid entry twice and check that the number and the
content are the same; generate receipts for ten entries and check that the numbers are distinct.

**Acceptance Scenarios**:

1. **Given** a paid entry, **When** the teacher generates its receipt, **Then** they get a PDF with
   studio name, student name, amount, date, method, receipt number and the statement that it is
   not a tax document, in the language chosen in the portal (Italian or English).
2. **Given** an entry that already has a receipt, **When** it is generated again, **Then** the same
   number is used and the content is the same.
3. **Given** twenty receipts generated at the same time in one studio, **Then** the numbers are
   all different and none is skipped or repeated.
4. **Given** a reversed entry, **When** the receipt of the original is opened, **Then** it carries a
   clear "cancelled" mark; a receipt cannot be generated for a reversal entry, nor for an entry
   that is not paid.
5. **Given** a parent linked to a student, **When** they open the receipts of that student,
   **Then** they can download issued receipts and nothing else; a parent of another student gets
   "not found".
6. **Given** a family whose data was erased at their request, **When** the studio opens the
   register, **Then** amounts, dates and receipt numbers are still there, and the name no longer
   appears: receipts show an anonymised label instead of the former name.

---

### Edge Cases

- A reversal changes the package status: if the reversed entry was the only paid entry covering
  a package, that package is open again and its student's payment status in the roster updates;
  lessons already completed are not touched.
- A reversal is dated the day the correction is made, never backdated, so a period already
  handed to the accountant does not change.
- Days and months are computed in the studio's local time (Europe/Rome), not in UTC: a payment
  at 23:30 belongs to its local day.
- Names with accents, commas, quotes or very long text appear correctly in the file, the
  document and the receipt.
- A parent linked to students of two studios sees each studio's instructions next to the right
  student's packages.
- Removing the instructions makes them disappear from the portal immediately.
- Online (card) entries from the existing test-mode integration appear in the register like any
  other entry and follow the same rules.
- A very large period (a whole year with thousands of entries) must still export.
- A receipt for a student whose family erased their data shows the anonymised label.

## Requirements *(mandatory)*

### Functional Requirements

**Register integrity**

- **FR-001**: A paid entry MUST NOT be editable or deletable through the product by any role; its
  amount, date, method, student and package stay as recorded.
- **FR-002**: A teacher or studio owner (within their own scope) MUST be able to reverse a paid
  entry, giving a reason of limited length; this creates a linked reversal entry and marks the
  original as reversed, and both stay visible.
- **FR-003**: A reversal MUST record who made it, when and why; it is dated on the day it is made.
- **FR-004**: An entry MUST be reversible at most once, and a reversal entry MUST NOT itself be
  reversed; to put a payment back, a new payment is recorded.
- **FR-005**: Reversing the entry that made a package paid MUST make the package open again when
  no other paid entry covers it.
- **FR-006**: Pending and overdue entries MUST stay editable and removable; their removal MUST be
  recorded in the audit log.
- **FR-007**: Reversing an online (card) entry MUST state on screen that no refund is made.
- **FR-008**: Every creation, reversal and removal of a register entry MUST be recorded in the
  audit log with actor, time, target and request identifier.
- **FR-009**: Concurrent attempts to reverse the same entry MUST produce exactly one reversal.

**Register views and export**

- **FR-010**: Users MUST be able to open the register for a day, a month or a custom period and see
  each entry with its status (paid, pending, overdue, reversed, reversal).
- **FR-011**: The register MUST show, for the period, totals received, reversed and net, overall
  and per payment method; only paid entries and their reversals count.
- **FR-012**: Totals and period boundaries MUST use the studio's local time.
- **FR-013**: A teacher MUST see only their own students' entries; a studio owner MUST see the
  whole studio; parents and students MUST NOT see the register.
- **FR-014**: Users MUST be able to export a period as a spreadsheet-friendly file with one row
  per entry (date, receipt number when any, student, method, amount, status, reason and link for
  reversals, package) and as a printable document with the studio name, the period, the totals
  per method and the production date.
- **FR-015**: Exports MUST neutralise values that a spreadsheet could run as a formula.
- **FR-016**: Each export MUST be recorded in the audit log (who, when, period), without storing
  its content.
- **FR-017**: The period of one export MUST be limited to a reasonable maximum (at most one year)
  and a longer request MUST be refused with a clear message.

**Payment instructions**

- **FR-018**: A studio owner (a teacher working alone is their own owner) MUST be able to save, for
  the studio: account holder, IBAN, optional bank name, an optional short note, and up to five
  external payment links, each with a label.
- **FR-019**: The system MUST validate IBAN format and checksum, and MUST accept only `https`
  addresses for links.
- **FR-020**: Teachers of the studio MUST be able to read the instructions and MUST NOT change them.
- **FR-021**: A parent or adult student MUST see the instructions of their studio next to each
  open (unpaid) package of the student they are linked to, with the statement that payment happens
  outside the product and is not verified by it; they MUST see nothing when the student has no open
  package or the studio has no instructions.
- **FR-022**: Instructions MUST be invisible to other studios and to anonymous visitors.
- **FR-023**: Bank details MUST be protected at rest, MUST NOT appear in logs, error reports or the
  audit log, and MUST be included in the studio owner's own data export and removed when that
  account is erased.
- **FR-024**: Every change to the instructions MUST be recorded in the audit log with who and when.

**Receipts**

- **FR-025**: A teacher or studio owner MUST be able to generate a PDF receipt for a paid entry in
  their scope, showing studio name, student name, amount, date, method, receipt number and the
  statement «not a tax document», in Italian or English according to the portal language.
- **FR-026**: A receipt number MUST be unique within a studio, assigned once at first generation,
  sequential within the calendar year, and never reused or changed.
- **FR-027**: Generating the same receipt again MUST give the same number and the same content.
- **FR-028**: A receipt MUST NOT be offered for an entry that is not paid or for a reversal entry;
  the receipt of a reversed entry MUST carry a clear "cancelled" mark.
- **FR-029**: A receipt MUST NOT contain any data beyond studio name, student name, amount, date,
  method and number: no bank details, no tax identifiers, no payer data.
- **FR-030**: A parent MUST be able to download the issued receipts of their own student, and
  nothing else.
- **FR-031**: When a family's data is erased at their request, the register, amounts, dates and
  receipt numbers MUST be kept, names MUST be anonymised, and receipts MUST show an anonymised label.

**Cross-cutting**

- **FR-032**: Every endpoint of this feature MUST refuse cross-studio reads and writes, answering
  "not found", and MUST ship with tests proving it.
- **FR-033**: All user-facing text MUST be available in Italian and English.
- **FR-034**: Existing paid entries MUST become non-editable on release without losing or altering
  any data, and existing clients' reads MUST keep working; the change of mutation rules MUST be
  documented in the public API contract.

### Key Entities *(include if feature involves data)*

- **Payment entry** (existing): an amount received or expected for a student and, optionally, a
  package, with a date, a method and a status. Gains: whether it was reversed, and a link to its
  reversal.
- **Reversal**: a register entry that cancels a paid entry; carries the reason, who made it, and
  when; linked one-to-one with the original.
- **Payment instructions**: one set per studio; account holder, IBAN, optional bank name and note,
  and up to five payment links (label and secure address).
- **Receipt**: one per paid entry at most; has a number unique within its studio and calendar year,
  the language, and who issued it and when.
- **Register period / summary**: not stored; the entries of a studio for a period with totals by
  status and method.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A teacher can correct a wrongly recorded paid entry and record the right one in under
  two minutes, and the original is still visible afterwards in 100% of cases.
- **SC-002**: For every combination of paid entries, reversals and methods in the test data, the
  net total shown equals a hand calculation (zero discrepancies).
- **SC-003**: The register for a month of a studio with 2,000 entries is shown in under 3 seconds.
- **SC-004**: A one-year export of 5,000 entries is produced in under 10 seconds and opens in a
  spreadsheet with no error and no cell treated as a formula.
- **SC-005**: A parent finds the payment instructions for an open package within two steps from the
  portal home.
- **SC-006**: In cross-studio tests, no user ever receives another studio's entries, totals,
  instructions or receipts (zero leaks).
- **SC-007**: 100% of receipts carry the non-fiscal statement, and twenty simultaneous generations
  in one studio produce twenty distinct, gapless numbers.
- **SC-008**: 100% of register-changing actions, exports and instruction changes have an audit
  record, and bank details appear in no log or error report in the tests.

## Assumptions

- MusicStudio stays free; studios are responsible for their own takings, taxes and accounting. The
  platform holds and moves no money, issues no tax invoices and verifies no bank transfer; this is
  stated in the terms of use (text to be finalised with a professional, outside this feature).
- The receipt names the student only. The system does not store who paid, and adding a payer name
  would add personal data (principle X, data minimisation); this can be revisited if studios ask.
- Currency is euro only, as in the existing payments.
- Instructions belong to the studio and are edited by its owner; a teacher working alone is the
  owner. Per-teacher instructions are not part of this feature.
- A paid entry stays "final" as in the existing rules; the reversal is the only correction. Pending
  and overdue entries are expectations rather than money received, so they stay editable.
- Receipt numbers restart each calendar year, with a prefix of the year (for example `2026-0001`).
- The mobile app on branch `mobile` reads the API contract from `main`. Removing the ability to
  edit and delete paid entries is a deliberate change of that contract; whether the mobile app uses
  those calls must be checked at planning time.
- The existing test-mode online payments are not changed; their entries follow the new rules.
- Out of scope: automatic card payments for studios (Stripe Connect), reading bank movements,
  electronic invoicing and links to invoicing services, refunds and disputes, any payout, and tax
  identifiers on receipts.
- The numbering "008" is only the next free directory: phase 7's text reserved "phase 008" for notes,
  progress and materials, so the roadmap in `CLAUDE.md` is updated when this feature is planned.
