# Feature Specification: Online Payments Straight to the Studio (Stripe Connect)

**Feature Branch**: `009-stripe-connect-payments`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Phase 9: real online payments from parents to studios through Stripe
Connect, with MusicStudio never holding or moving money and earning no commission. Owner's goal:
the app can be used for payments the way people pay today (cards such as Visa, wallets such as
PayPal where the provider supports them), so that a parent pays a lesson package online and the
money goes directly to the studio's own connected account; the platform takes no fee. Phase 3
already has Stripe Checkout in test mode, but the money would land on the platform's own account,
which contradicts the principle that the platform never holds money. Phase 8 built the studio cash
register (reversal entries, payment instructions, non-fiscal receipts) and left Stripe Connect,
automatic card payments, refunds and disputes out of scope. This phase brings Connect in scope:
each studio onboards a connected account (the provider collects identity verification, so
MusicStudio stores no identity documents), the studio owner sees the onboarding status, parents pay
a package online and the money goes to the studio's account with no platform fee, the payment is
recorded in the register as paid, and a refund or dispute is reflected in the register through the
reversal mechanism of phase 8, never by editing an entry. Free transfers between any two users are
out of scope. Test mode only until the owner decides otherwise; every provider call stays inside
`apps/payments/gateway.py`. The constitution (v3.1.1) must be checked. Terms of use and legal
wording are parked by the owner and listed as an open owner task. Italian study docs are a
deliverable."

## Constitution check (done before writing)

- **Principle IV** allows payment gateway integration in **test mode only**. Connect is a payment
  gateway integration, so it fits **as long as it stays in test mode**. Taking real money needs a
  deliberate change of that principle (a MINOR amendment through `/speckit-constitution`) and is
  **not part of this feature**: see "Out of scope" and the open owner tasks.
- **Principle IV** also lists phases 1–5 only; phases 6–8 were added without touching it. This
  feature does not change that wording, but the plan should note it.
- **Principle X** (privacy by design): card data never reaches the backend, and no identity
  document is stored. The product keeps only the connected account's identifier and a few status
  flags per studio. Provider events can carry personal data: logs and error reports must contain
  identifiers only.
- **Principles I, III, V, VIII, IX**: tenant isolation on every new endpoint, tests with cross-studio
  checks and query budgets, writes in services, an ADR, Italian study docs, and the OWASP walk.
- No principle forbids this feature. **No amendment is needed to build it in test mode.**

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A studio connects its own payment account (Priority: P1)

A studio owner (a teacher working alone is their own owner) opens the payments settings of the
portal and chooses to accept online payments. They are sent to the payment provider to create or
link the studio's own account: the provider asks for the studio's identity, bank account and
anything the law requires, and MusicStudio sees none of it. When they come back, the portal shows
the state of the account: not started, in progress, waiting for more information from the provider,
active, or restricted. The owner can resume an unfinished onboarding or open the provider's own
page to manage the account.

**Why this priority**: nothing else works until a studio has an account that can receive money.
It is also where the principle "the platform never holds money" becomes true: the money will have
a destination that is not the platform.

**Independent Test**: as a studio owner, start onboarding, leave halfway, come back and see
"in progress", complete it with the provider's test data and see "active"; as a teacher of the same
studio and as a parent, see no way to change it.

**Acceptance Scenarios**:

1. **Given** a studio with no connected account, **When** the owner starts onboarding, **Then** they
   are taken to the provider and, on return, the portal shows the current state of that account.
2. **Given** an onboarding left unfinished, **When** the owner opens the settings again, **Then**
   they can resume it, and the state reads "in progress" or "information needed".
3. **Given** an active account, **When** the owner opens the settings, **Then** they see "active" and
   a way to open the provider's own page to see balances, payouts and details.
4. **Given** an account the provider later restricts (for example, documents expired), **When** the
   provider tells MusicStudio, **Then** the state becomes "restricted", the owner is told what to
   do on the provider's side, and online payment stops being offered to parents (User Story 2).
5. **Given** a teacher of the studio who is not the owner, a parent or an adult student, **When**
   they try to start, change or read the account settings, **Then** teachers may read the state but
   not change it, and parents and students get "not found".
6. **Given** a studio of another owner, **When** anyone tries to read or change this studio's
   account state, **Then** the answer is "not found" and nothing changes.
7. **Given** a studio where the owner has never started onboarding, **Then** nothing about it is
   shown to parents and everything built in phase 8 keeps working as it does today.

---

### User Story 2 - A parent pays a package online, the money goes to the studio (Priority: P1)

A parent opens the portal, sees their child's open package and, if the studio has an active
account, a button to pay online. They are sent to the provider's payment page, choose how to pay
(card, or a wallet such as PayPal where the provider supports it for that studio), and come back.
The money goes to the studio's account; MusicStudio never receives it and takes no fee. A moment
later the package shows as paid and the payment appears in the studio's register as paid, with the
method "online". The parent can then download the receipt of phase 8.

**Why this priority**: this is the point of the feature and what the owner asked for: paying the way
people pay today, with the studio as the receiver.

**Independent Test**: with an active test account, pay an open package with a test card; check that
the register shows one paid entry of the right amount, the package is paid, and the money is on the
studio's account and not on the platform's.

**Acceptance Scenarios**:

1. **Given** an open package of a student and an active studio account, **When** a linked parent
   chooses to pay online, **Then** they are taken to the provider's payment page for the amount of
   that package, in euros, and nothing is charged to the platform.
2. **Given** a successful payment, **When** the provider confirms it, **Then** exactly one paid
   entry is recorded in the studio's register, linked to the package and the student, with the
   method "online", and the package is paid, even if the confirmation arrives twice.
3. **Given** the parent closes the page after paying, **Then** the payment is still recorded, because
   it does not depend on the parent coming back.
4. **Given** a payment that fails, is cancelled or expires, **Then** no paid entry exists, the
   package stays open, and the parent can try again.
5. **Given** two clicks on "pay" or two open payment pages for the same package, **Then** the
   package can be paid only once (a second payment for an already paid package is not accepted
   or is flagged for the studio, never silently double-counted).
6. **Given** a studio without an active account (not started, in progress, restricted), **When** a
   parent opens the portal, **Then** no online payment is offered and the phase 8 payment
   instructions are shown as before; an attempt to start an online payment through the API is
   refused with a clear message.
7. **Given** a parent of another studio or student, **When** they try to pay for a package that is
   not theirs, **Then** the answer is "not found".
8. **Given** the provider is unreachable when the parent chooses to pay, **Then** they get a clear
   "payments are unavailable, try again or use the instructions" message and nothing is recorded.
9. **Given** a paid online entry, **When** the studio opens the register, **Then** it is final like
   any other paid entry and follows every rule of phase 8 (no edit, no deletion, correction only by
   reversal), and the receipt can be generated.

---

### User Story 3 - Refunds and disputes show up in the register as reversals (Priority: P2)

A studio refunds a parent from the provider's own page (the studio, not MusicStudio, decides and
does it), or a card holder disputes a payment. The provider tells MusicStudio, and the studio's
register gets a reversal entry linked to the original payment, saying the cause (refund or dispute),
dated the day it happened. The original stays visible, the package becomes open again if nothing
else covers it, and the totals come out right. Nothing is ever edited or deleted.

**Why this priority**: without it, the register would say "paid" for money that went back, and an
accountant's totals would be wrong. It builds directly on the reversal mechanism of phase 8.

**Independent Test**: pay a package, refund it fully on the provider's side, and check that one
reversal entry appears with the cause "refund", the package is open again and the net total is zero;
repeat with a dispute.

**Acceptance Scenarios**:

1. **Given** a paid online entry, **When** the studio refunds it fully on the provider's side,
   **Then** one reversal entry is created, linked to the original, with the cause "refund", dated
   that day.
2. **Given** a refund of part of the amount, **Then** the register records it and never leaves a
   wrong total (see Edge Cases for how a partial refund is represented).
3. **Given** a dispute opened on a payment, **Then** the register shows the payment as under dispute
   and, if the studio loses, a reversal with the cause "dispute"; if the studio wins, nothing is
   reversed and the entry returns to normal.
4. **Given** the same refund notified twice, **Then** only one reversal exists.
5. **Given** a refund of a payment recorded by hand (cash, bank transfer) or one that does not exist
   in the register, **Then** nothing is changed and the event is kept for the studio to see.
6. **Given** a studio that reverses an online entry in the register itself (phase 8, "correct a
   mistake"), **Then** the screen still says that no money is returned: the register is corrected and
   nothing is refunded; refunds are made on the provider's side.
7. **Given** the reversal of an online payment, **Then** the receipt of the original carries the
   "cancelled" mark as in phase 8.

---

### User Story 4 - Studios that do not connect keep working as before (Priority: P2)

A studio that never connects an account keeps recording payments by hand, showing payment
instructions to parents, and issuing receipts, exactly as in phase 8. Online payment is an option a
studio turns on, not an obligation.

**Why this priority**: most small studios start with cash and bank transfers; breaking that would
turn a free option into a requirement.

**Independent Test**: with a studio that has no connected account, run the whole phase 8 walk
(register, totals, export, instructions, receipt) and see no difference.

**Acceptance Scenarios**:

1. **Given** a studio with no connected account, **Then** every flow of phase 8 behaves as before.
2. **Given** a studio that connects an account later, **Then** earlier register entries are not
   touched.
3. **Given** the platform's own earlier online-payment path (phase 3, money on the platform's
   account), **Then** it is no longer available to any studio: online payment exists only through
   the studio's own account (see Assumptions).

---

### Edge Cases

- **Partial refund**: the original payment cannot be left as "paid in full" when only part came
  back. The register must show the net amount correctly. How a partial refund is represented
  (a reversal of the refunded amount, with the original marked as partly reversed) is decided in
  the plan; the totals must be right in every case.
- **Amount mismatch**: the provider confirms an amount different from the package's current price
  (for example, the price changed while the page was open). The paid entry records what was really
  paid, and the studio is told when it differs from the package.
- **Wrong or unknown account**: an event that names an account no studio is linked to, or that does
  not match the studio of the attempt, is ignored, kept for inspection and never recorded as a
  payment.
- **Currency other than euro**: refused or ignored; euro only.
- **Payment that completes after the studio's account became restricted**: the money is already on the
  provider's side; the payment is recorded normally.
- **Confirmation that arrives before the return of the parent, or never**: the register does not
  depend on the return page; a periodic check closes attempts whose confirmation was lost.
- **Studio changes owner or is deleted**: the link to the account is removed with the studio's data;
  the money already paid stays with the account, which is the studio's, not the platform's.
- **Family erases their data**: the register keeps amounts, dates and receipt numbers and anonymises
  names, as in phase 8; no payer detail beyond that is stored.
- **A parent linked to children of two studios** pays each package to the right studio's account.
- **Test mode**: the studio's onboarding and every payment use the provider's test data; no real
  money moves, and the portal says so clearly wherever a payment can be started.
- **The owner of the platform has no way to move or see a studio's money.** The product has no
  payout, transfer or balance screen.

## Requirements *(mandatory)*

### Functional Requirements

**Studio account and onboarding**

- **FR-001**: A studio owner MUST be able to start, resume and complete the creation or linking of
  the studio's own payment account with the provider; a teacher working alone is their own owner.
- **FR-002**: The system MUST store only what it needs about that account: the provider's identifier
  of the account and its state (not started, in progress, information needed, active, restricted).
  It MUST NOT store identity documents, bank details of the account or any data the provider
  collects during verification.
- **FR-003**: The state of the account MUST follow the provider's own information, kept up to date
  without the owner having to do anything, and MUST be readable by the owner and by the studio's
  teachers; only the owner MUST be able to start or change it.
- **FR-004**: The owner MUST be able to reach the provider's own page for the account (balances,
  payouts, refunds, details) from the portal.
- **FR-005**: Every start, change of state and disconnection of the account MUST be recorded in the
  audit log with actor (or "provider"), time and target, without storing provider secrets.
- **FR-006**: Parents, students and users of other studios MUST NOT see or change a studio's account
  settings; cross-studio access MUST answer "not found".

**Paying online**

- **FR-007**: A parent or adult student MUST be able to start an online payment for an open package
  of a student they are linked to, only when the studio's account is active.
- **FR-008**: The payment MUST go to the studio's own account and MUST NOT pass through an account
  of the platform; the platform MUST NOT charge any fee or commission.
- **FR-009**: The amount MUST be the package's price at the moment the payment starts, in euros; the
  parent MUST see the amount and the studio's name before paying.
- **FR-010**: A payment MUST be recorded in the studio's register as a paid entry only when the
  provider confirms it, once, linked to the student and package, with the method "online"; a
  repeated confirmation MUST NOT create a second entry.
- **FR-011**: A payment MUST NOT depend on the parent returning to the portal; a periodic check MUST
  settle attempts whose confirmation did not arrive.
- **FR-012**: A failed, cancelled or expired attempt MUST NOT create a paid entry and MUST leave the
  package open.
- **FR-013**: A package MUST NOT be double paid through two attempts; a second confirmation for an
  already paid package MUST be kept visible to the studio and never counted twice silently.
- **FR-014**: When the studio's account is not active, the system MUST NOT offer online payment and
  MUST refuse an attempt through the API with a clear message; payment instructions (phase 8) stay
  available.
- **FR-015**: A provider that is unreachable MUST give the parent a clear message and MUST NOT leave
  anything half-recorded.
- **FR-016**: The paid online entry MUST follow every rule of phase 8: final, corrected only by
  reversal, covered by the register's totals, exports and receipts.

**Refunds and disputes**

- **FR-017**: When the provider reports that a payment was refunded in full, the system MUST create
  one reversal entry linked to the original, with the cause "refund", dated the day it happened.
- **FR-018**: When the provider reports a dispute, the system MUST mark the payment as under dispute
  and, if the dispute is lost, create a reversal with the cause "dispute"; if it is won, the payment
  MUST return to normal and nothing is reversed.
- **FR-019**: A partial refund MUST be reflected so that the net total of the register matches the
  money actually kept by the studio (representation decided in the plan).
- **FR-020**: A refund or dispute MUST NEVER edit or delete an existing entry; the original stays
  visible and the reversal is a new, linked entry (phase 8 rules).
- **FR-021**: A repeated notification of the same refund or dispute MUST NOT create a second reversal.
- **FR-022**: A refund of a payment that is not in the register, or that was recorded by hand, MUST
  NOT change anything and MUST be kept for the studio to see.
- **FR-023**: A reversal made by the studio in the register of an online entry MUST state on screen
  that no money is returned; refunds are made on the provider's side.
- **FR-024**: Reversing an online entry MUST make the package open again when no other paid entry
  covers it (phase 8 rule), whatever the cause.

**Provider events and security**

- **FR-025**: Every provider notification MUST be checked for authenticity before anything is
  recorded, MUST be processed once even if it arrives several times, and MUST be attributed to the
  right studio through the account it names; events for unknown accounts MUST be ignored and kept.
- **FR-026**: A slow or failed processing of a notification MUST NOT lose it or make it count twice:
  it is kept and settled later, once.
- **FR-027**: Logs, error reports and the audit log MUST contain identifiers only: no names, emails,
  card or bank details, even when the provider sends them.
- **FR-028**: Every call to the provider MUST stay inside the single gateway module; the rest of the
  code works with plain data objects, and tests replace the gateway.
- **FR-029**: The product MUST run in the provider's **test mode only**; a live key MUST stop
  start-up as it does today, and the portal MUST state that payments are tests wherever one can
  start.
- **FR-030**: The platform MUST NOT offer any payout, transfer, balance or movement of money
  between users or to the platform.

**Cross-cutting**

- **FR-031**: Every new endpoint MUST refuse cross-studio reads and writes ("not found"), ship with
  tests proving it and, on the main reads, assert its query count.
- **FR-032**: All user-facing text MUST be available in Italian and English.
- **FR-033**: The public API contract and the generated types MUST be updated, and the change in the
  contract (the removal of the earlier platform-account payment path, new fields) MUST be
  documented; whether the mobile app on branch `mobile` uses the removed path MUST be checked at
  planning time.
- **FR-034**: Existing paid entries and existing online entries recorded in test mode MUST keep their
  data; nothing recorded in earlier phases is altered or lost.

### Key Entities *(include if feature involves data)*

- **Studio payment account**: one per studio at most; the provider's identifier of the studio's own
  account, its state, and when that state last changed. No identity or bank data.
- **Online payment attempt** (existing, extended): a try to pay a package; now belongs to the
  studio's account, has the amount asked, and is settled by a provider confirmation, a failure, an
  expiry or the periodic check.
- **Payment entry** (existing, phase 8): gains nothing new in shape, except the cause of a reversal
  (manual correction, refund, dispute) and a "under dispute" indication.
- **Provider event** (existing, extended): a stored notification, with the account it names, so it is
  processed once and attributed to a studio.
- **Audit record** (existing): receives the new actions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A studio owner with the provider's test data can go from "not connected" to "active"
  in under 10 minutes, and the portal shows the right state at each step.
- **SC-002**: A parent pays an open package online in under 2 minutes from the portal home, and the
  package shows as paid within 1 minute of the provider's confirmation.
- **SC-003**: In every online payment of the test suite, the money is on the studio's account and the
  platform's account has none of it (zero payments that pass through the platform).
- **SC-004**: Among the payments confirmed more than once, the same refund notified several times and
  two simultaneous attempts, the register ends with exactly one entry or one reversal each time
  (zero duplicates).
- **SC-005**: For every combination of payments, full and partial refunds, disputes and manual
  reversals in the test data, the net total of the register equals a hand calculation (zero
  discrepancies).
- **SC-006**: In cross-studio tests, no user ever starts, reads or changes another studio's account,
  attempts, entries or events (zero leaks).
- **SC-007**: 100% of onboarding actions, state changes, online payments, refunds and disputes have
  an audit record, and no personal or financial detail from the provider appears in any log or
  error report in the tests.
- **SC-008**: A studio that never connects an account passes the whole phase 8 walk unchanged.
- **SC-009**: The full flow (onboarding, payment, refund) is run end to end once against the
  provider's test environment and the result is recorded in the study documentation.

## Assumptions

- **Money**: the studio is the merchant and receives the money on its own account; MusicStudio
  holds and moves none, issues no tax documents and takes no fee. Fees charged by the provider on
  the payment, refunds and disputes are those of the studio's own account and are the studio's
  responsibility; the product shows no fee calculation. This is stated in the terms of use, whose
  text is parked by the owner (see open owner tasks).
- **Account type**: the kind of provider account that makes the studio the merchant and costs the
  platform nothing per studio is chosen in the plan, after checking the provider's current pricing
  and rules; this specification only requires the outcomes above.
- **Test mode**: the whole feature runs in test mode, as required by Principle IV. In test mode no
  real money moves, so this phase delivers the capability, not live takings.
- **Wallets such as PayPal** are offered only if the provider supports them for that studio's account
  and country; the choice of methods is the provider's, configured on its side, not coded here.
- **The earlier platform-account path** of phase 3 is removed for studios: online payment exists only
  through the studio's own account. Nothing real was ever paid through it (test mode only), so no
  data or money is at stake, and the existing online entries stay in the register.
- **Refunds and disputes are made on the provider's side by the studio**; MusicStudio reflects them.
  A "refund" button inside MusicStudio is not part of this feature.
- **Currency** is euro only, as before.
- **Who pays**: parents and adult students linked to the student, as in phase 8. No anonymous payment.
- **A studio has at most one account**; a teacher of a studio does not have their own.
- **Receipts** (phase 8) are available for paid online entries exactly like any paid entry, and show
  the same data; no payer detail is added (Principle X).
- The mobile app on branch `mobile` reads the contract from `main`; any change to calls it uses is
  checked at planning time.
- Italian study documentation (concept file, ADR, glossary, interview Q&A, OWASP walk, index) is a
  deliverable of this phase, as in the previous ones.

## Out of scope

- **Real money (live mode).** Going live needs, outside this feature: the owner's decision, the
  provider's own checks on the platform's account, a change of Principle IV through
  `/speckit-constitution`, and the terms of use (below). It is a separate step.
- Free transfers between any two users, wallet balances, payouts or any movement of money by the
  platform: these are regulated payment services and are not offered.
- A refund or dispute-handling screen inside MusicStudio (the studio acts on the provider's page).
- Electronic invoicing, tax identifiers on receipts, reading bank movements.
- A second provider (PayPal direct, Satispay): wallets are reached only through the provider.
- Subscriptions, instalments, discounts and coupons.

## Open owner tasks (outside the code)

- **T-owner-1: terms of use and legal wording.** Parked by the owner on 2026-11-16. Before real
  studios use online payments: terms stating that the platform holds no money, takes no fee, is not
  a party to the payment and is not responsible for refunds, disputes or taxes; the wording of the
  receipt ("not a tax document", phase 8 T063); a professional's check.
- **T-owner-2: the provider's platform account.** Creating and verifying the platform's own account
  with the provider (Connect enabled, business details, branding) is done by the owner, with the
  provider; test mode needs only the test platform profile.
- **T-owner-3: decision to go live.** A written decision, the constitution amendment and a first
  real payment of a small amount between people the owner knows.
