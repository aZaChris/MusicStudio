# Feature Specification: Security, Privacy and Accounts (Phase 007)

**Feature Branch**: `staging/backend`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Phase 007 — security, privacy and accounts. We handle minors' data
and payments, so security and privacy are first-class: constitution principles, self-service
owner registration and invitations, email verification and password reset without account
enumeration, optional TOTP MFA, progressive lockout, read-only adult student accounts, recorded
parental consent, GDPR export/erasure/retention, audit log, encryption of sensitive fields,
IDOR tests, secret scanning and personal-data-free logs, Italian draft record of processing and
privacy notice, web portal screens. Coolify, no AWS, Stripe test mode only, no SMS. Out of
scope: lesson recurrences, progress/notes/materials (phase 008), Stripe Connect."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A studio owner signs up alone (Priority: P1)

A music teacher who has never used MusicStudio opens the portal, creates an account with
their studio, confirms their email address from the message they receive, and starts working.
Nobody has to create the account for them from a server terminal.

**Why this priority**: today accounts exist only through operator commands. Without
self-service sign-up there is no product to put in front of a real teacher.

**Independent Test**: from an empty system, register, follow the confirmation link from the
email, sign in, and see an empty studio dashboard.

**Acceptance Scenarios**:

1. **Given** no account for an address, **When** a person registers with name, email, password,
   studio name and accepts the terms and privacy notice, **Then** an unconfirmed account and its
   studio are created, a confirmation email is sent, and the person is told to check their inbox.
2. **Given** an unconfirmed account, **When** the person signs in, **Then** sign-in is refused
   with a message that offers to resend the confirmation.
3. **Given** a confirmation link, **When** it is opened within its validity, **Then** the account
   becomes confirmed and the link stops working; **When** it is opened after expiry or a second
   time, **Then** a clear message offers a new link.
4. **Given** an address that already has an account, **When** someone registers with it,
   **Then** the screen shows the same message as a new registration, and the existing owner
   receives an email saying someone tried to register with their address.
5. **Given** a password that is too short, too common or similar to the email, **When** the
   person registers, **Then** the form explains which rule failed and nothing is created.

---

### User Story 2 - Recover a forgotten password safely (Priority: P1)

Any user who forgets their password asks for a reset link, chooses a new password, and every
other session on their account ends. An attacker cannot learn from the screen whether an
address is registered.

**Why this priority**: without self-service reset every forgotten password is an operator
ticket, and a careless reset flow is the most common way accounts are stolen.

**Independent Test**: request a reset for a registered and an unregistered address, compare
the responses, complete the reset from the email, and check that old sessions are gone.

**Acceptance Scenarios**:

1. **Given** any address, **When** a reset is requested, **Then** the response is identical in
   content and comparable in timing whether the address exists or not.
2. **Given** a registered address, **When** a reset is requested, **Then** a single-use link
   valid for 1 hour is emailed.
3. **Given** a valid link, **When** a new password is set, **Then** the link stops working, all
   existing sessions of that account end, and the user receives a "your password was changed"
   email.
4. **Given** several reset requests in a row, **When** the user opens an older link after a
   newer one was used, **Then** the older link no longer works.

---

### User Story 3 - Owners invite teachers and parents (Priority: P1)

A studio owner invites a teacher by email; a teacher or owner invites the parent of one or more
of their students. The invited person sets their own password from the invitation, and for a
parent of a minor the acceptance records their consent to the processing of their child's data.

**Why this priority**: teachers and parents must be able to join without anyone knowing or
choosing their password, and parental consent is the legal basis we rely on for minors.

**Independent Test**: as an owner, invite a teacher and, as a teacher, invite a parent for a
student; accept both invitations from the emails; sign in as each and see only what the role
allows; check the consent record for the parent.

**Acceptance Scenarios**:

1. **Given** an owner, **When** they invite an email as a teacher, **Then** an invitation valid
   for 7 days is emailed and appears as pending in the studio's team list.
2. **Given** a teacher, **When** they invite an email as parent of one of their own students,
   **Then** an invitation is emailed; **When** they try with a student of another teacher or
   studio, **Then** it is refused as if the student did not exist.
3. **Given** a pending invitation, **When** the invited person opens it, sets a password and,
   for a parent, confirms the privacy notice and the consent for their children, **Then** the
   account is created already confirmed, linked to the right studio or students, and the
   consent is recorded with who, when and which notice version.
4. **Given** an invitation for an address that already has a parent account, **When** it is
   accepted after sign-in, **Then** the new children are linked to the existing account and no
   second account is created.
5. **Given** an expired, already used or revoked invitation, **When** it is opened, **Then** it
   is refused with a message to ask for a new one.
6. **Given** an owner, **When** they revoke a pending invitation, **Then** it stops working.

---

### User Story 4 - Nobody sees what is not theirs (Priority: P1)

A teacher only reaches their own students and their data; a parent only their own children;
an owner only their own studio; a student only themselves. Guessing or changing identifiers
never reveals or changes someone else's data.

**Why this priority**: the system holds children's data and payment records. Object-level
authorization is the requirement everything else depends on; it is proven per endpoint, not
assumed.

**Independent Test**: for every endpoint, two users of different teachers, families and studios
try to read, list, change and delete each other's objects; every attempt fails as "not found".

**Acceptance Scenarios**:

1. **Given** two teachers in the same studio, **When** one requests a student, lesson, package
   or payment of the other by identifier, **Then** the response is "not found" — unless the
   requester is the studio's owner, who sees the whole studio.
2. **Given** two studios, **When** an owner of one requests or modifies any object of the other,
   **Then** the response is "not found" and nothing changes.
3. **Given** a parent with one child, **When** they request another child, its lessons or its
   payments, **Then** the response is "not found".
4. **Given** a write that references an object outside the requester's scope (for example
   booking a lesson for another teacher's student), **When** it is submitted, **Then** it is
   rejected and nothing is written.
5. **Given** the new endpoints of this phase (invitations, consent, export, erasure, audit log,
   MFA), **When** another user's identifiers are used, **Then** the same rules hold.

---

### User Story 5 - Sign-in that resists guessing and theft (Priority: P2)

Repeated wrong passwords temporarily lock the account; owners and teachers can turn on a
second factor with an authenticator app and keep recovery codes for when the phone is lost.

**Why this priority**: owners and teachers can see many children's data and record payments;
their accounts are the most valuable target. It builds on the sign-in of stories 1–3.

**Independent Test**: fail the password several times and verify the lock and its duration;
enable the second factor, sign in with a code, sign in with a recovery code, then disable it.

**Acceptance Scenarios**:

1. **Given** an account, **When** the wrong password is entered 5 times in a row, **Then** the
   account refuses sign-in for 15 minutes, every further lock doubles the wait up to 24 hours,
   and a correct sign-in resets the count. The message does not reveal whether the account
   exists.
2. **Given** a locked account, **When** the owner of the account completes a password reset,
   **Then** the lock is lifted.
3. **Given** an owner or teacher, **When** they enable the second factor, **Then** they scan a
   code with an authenticator app, confirm one current code, and receive 10 single-use recovery
   codes shown once.
4. **Given** the second factor is on, **When** the user signs in, **Then** a valid password alone
   gives no access until a current code or an unused recovery code is entered; a used recovery
   code never works again.
5. **Given** the second factor is on, **When** the user disables it, **Then** they must enter
   their password and a current code.
6. **Given** a user who lost both the phone and the codes, **When** they ask the operator,
   **Then** the operator can remove the second factor from the server side, and the action is
   audited.

---

### User Story 6 - Families control their data (Priority: P2)

A parent (or an adult student) downloads all the data the studio holds about them and their
children, and can ask for it to be erased. Erasure removes what is not needed and anonymises
what the law requires the studio to keep.

**Why this priority**: export and erasure are rights under GDPR and a precondition for
publishing the app in the stores; they depend on accounts and consent from stories 1–3.

**Independent Test**: as a parent, download the export and check that it contains every record
about them and their children and nothing about other families; request erasure and check
what disappears, what stays anonymised, and that sign-in no longer works.

**Acceptance Scenarios**:

1. **Given** a parent, **When** they request their export, **Then** they receive a single
   machine-readable file with their account, their children, the children's lessons, packages
   and payments, the consents they gave, and nothing about other families or internal teacher
   notes about other students.
2. **Given** a parent, **When** they request erasure and confirm with their password, **Then**
   their account is closed at once, sessions end, and their personal data and their children's
   are erased or anonymised; payment records are kept with the amounts and dates but without
   names, for the legal retention period.
3. **Given** a child linked to two parents, **When** one parent requests erasure, **Then** only
   that parent's account is erased and the child's data stays while another parent remains
   linked; the teacher is told that one parent left.
4. **Given** an owner, **When** they archive a student, **Then** the student's personal data is
   anonymised automatically once the retention period after the last activity ends.
5. **Given** an export or erasure, **When** it happens, **Then** it is recorded in the audit log.

---

### User Story 7 - Adult students see their own lessons (Priority: P3)

An adult student, invited by their teacher, signs in and sees their lessons, packages and
payments without being able to change anything. A minor has no account of their own; their
parent sees for them.

**Why this priority**: useful but not blocking; studios with adult students work today through
the teacher.

**Independent Test**: mark a student as adult, invite them, accept, sign in and check the
read-only view; try the same with a minor and see it refused.

**Acceptance Scenarios**:

1. **Given** a student marked as adult, **When** the teacher invites them, **Then** they can
   accept, sign in and see only their own lessons, packages and payments, read-only.
2. **Given** a student marked as minor, **When** the teacher tries to invite them as a student,
   **Then** it is refused with a message to invite the parent instead.
3. **Given** a student account, **When** it tries any change, **Then** it is refused.

---

### User Story 8 - The owner can see who did what (Priority: P3)

An owner reviews the sensitive actions in their studio: sign-ins, password and second-factor
changes, invitations, role changes, exports, erasures and payments. The operator sees the same
for the whole system.

**Why this priority**: required to investigate an incident and to answer a family's question
"who looked at my child's data"; it records events produced by the other stories.

**Independent Test**: perform each sensitive action and check that it appears once, with who,
when, what and the outcome, in the owner's view, and that a teacher cannot see the log.

**Acceptance Scenarios**:

1. **Given** each sensitive action, **When** it happens, **Then** an entry records actor, action,
   target, time, outcome and request identifier, without passwords, codes, tokens or card data.
2. **Given** an owner, **When** they open the audit view, **Then** they see only their studio's
   entries, newest first, filterable by action and date.
3. **Given** any user, **When** they try to change or delete an audit entry, **Then** it is not
   possible through the product.

---

### Edge Cases

- A person registers, never confirms: the unconfirmed account and its studio are deleted after
  7 days, so the address becomes free again.
- An invitation is accepted while the inviting teacher has since left the studio: the
  invitation was revoked when they left, so it is refused.
- A user changes their email: the new address must be confirmed before it replaces the old one,
  and the old address receives a notice.
- Two password resets are requested a minute apart: only the newest link works.
- A parent requests erasure while a payment for their child is pending online: the erasure
  waits until the payment is settled or expired, and the parent is told why.
- An owner requests erasure of their own account: refused while the studio has other active
  teachers or students; the owner must close the studio first, which erases the studio's data
  following the same retention rules.
- The clock of a phone drifts: authenticator codes are accepted within one step before and
  after the current one, and a code already used is not accepted twice.
- The encryption key is rotated: data written with the old key stays readable until it is
  re-encrypted with the new one.
- A bot fills the registration form many times: registrations from one address are rate limited
  like sign-in.
- Logs and error reports: never contain passwords, codes, tokens, email bodies or lesson notes;
  identifiers only.

## Requirements *(mandatory)*

### Functional Requirements

**Principles and documentation**

- **FR-001**: The project constitution MUST gain explicit security and privacy principles
  (privacy by design and by default, data minimisation, minors only through a parent, audit of
  sensitive actions, encryption of sensitive content, secrets never in the repository or its
  history), recorded with a decision record.
- **FR-002**: The project MUST include an Italian draft record of processing activities and an
  Italian draft privacy notice for families and for teachers, each clearly marked as a draft to
  be validated by a qualified professional, with a version identifier the product references.

**Accounts**

- **FR-003**: A person MUST be able to register as studio owner with name, email, password,
  studio name and acceptance of terms and privacy notice; the account stays unusable until the
  email is confirmed.
- **FR-004**: Registration, confirmation resend and password reset MUST give the same visible
  response whether or not the address is registered.
- **FR-005**: Confirmation links MUST be single-use and expire after 48 hours; reset links MUST
  be single-use, expire after 1 hour, and be invalidated by any later password change.
- **FR-006**: Setting a new password (by reset or by change) MUST end all other sessions of the
  account and send a notice to the account's address.
- **FR-007**: Owners MUST be able to invite teachers; owners and teachers MUST be able to invite
  parents of students in their scope and adult students; invitations expire after 7 days, are
  single-use and revocable, and are revoked automatically when the inviter loses access.
- **FR-008**: Accepting an invitation MUST let the invited person choose their own password and
  create an already-confirmed account with the role and links stated in the invitation; an
  existing account with the same address gains the links instead of a duplicate.
- **FR-009**: Students MUST carry an "adult" indicator set by the teacher; only adult students
  can receive a student account, which is read-only and limited to their own data.
- **FR-010**: Unconfirmed self-registered accounts MUST be removed 7 days after registration.

**Sign-in protection**

- **FR-011**: After 5 consecutive failed sign-ins an account MUST be locked for 15 minutes,
  doubling at each further lock up to 24 hours; a successful sign-in or a password reset resets
  it; responses must not reveal whether the account exists.
- **FR-012**: Owners and teachers MUST be able to enable and disable a time-based second factor
  with an authenticator app and 10 single-use recovery codes; when enabled, sign-in requires it.
- **FR-013**: The operator MUST be able to remove a user's second factor and to unlock an
  account, both audited.
- **FR-014**: Registration, reset, confirmation resend, invitation acceptance and second-factor
  verification MUST be rate limited per client like sign-in.

**Consent and privacy rights**

- **FR-015**: The system MUST record each consent given (who, for which children, when, which
  notice version) and show it to the parent; withdrawing consent MUST be possible and start
  erasure of the affected children's data.
- **FR-016**: A parent or adult student MUST be able to download, in one machine-readable file,
  all data held about them and their children, and nothing else.
- **FR-017**: A parent or adult student MUST be able to request erasure, confirmed by password;
  personal data is erased or anonymised, payment records are kept anonymised for the legal
  retention period, and the account can no longer sign in.
- **FR-018**: Data of archived students MUST be anonymised automatically 24 months after their
  last lesson or payment; payment records older than the legal retention period (10 years) MUST
  be deleted; audit entries MUST be kept 12 months; a periodic job applies these rules.
- **FR-019**: The product MUST collect only the personal data it uses: no date of birth (only the
  adult indicator), no phone number, no address, no card data.

**Protection of data**

- **FR-020**: Free-text notes about lessons MUST be stored encrypted with a key that is provided
  by the environment and can be rotated without losing existing data; the rotation procedure is
  documented.
- **FR-021**: Every sensitive action (sign-in success and failure, lockout, password change and
  reset, second-factor changes, invitation sent, accepted and revoked, role and link changes,
  consent given and withdrawn, export, erasure, payment recorded or refunded, operator unlock)
  MUST produce an audit entry with actor, action, target, time, outcome and request identifier.
- **FR-022**: Audit entries MUST be visible to the studio owner for their studio only, never
  editable or deletable through the product, and never contain secrets or card data.
- **FR-023**: Logs and error reports MUST NOT contain passwords, codes, tokens, email addresses,
  names or note contents; an automated test MUST prove it for the sign-in, reset and invitation
  flows.
- **FR-024**: The repository and its full history MUST be scanned for secrets on every change,
  and a finding MUST block the change.
- **FR-025**: The production configuration MUST keep forcing HTTPS with HSTS, secure cookies,
  the existing security headers and the allow-listed browser origins; it MUST refuse to start
  without the encryption key.
- **FR-026**: The backend MUST never receive or store card data; online payments stay with the
  payment provider's hosted page in test mode, and the provider's notifications keep being
  verified by signature.

**Authorization**

- **FR-027**: Every endpoint — existing and new — MUST have tests proving that teachers, parents,
  students and owners of other scopes cannot read, list, change or delete objects outside their
  scope, and that out-of-scope objects answer "not found".

**Web portal**

- **FR-028**: The web portal MUST offer screens for registration, email confirmation, forgotten
  and new password, invitation acceptance (with consent for parents), team and invitation
  management for owners, parent invitation for teachers, second-factor setup and sign-in, the
  family's data page (consents, export, erasure), the student's read-only view, and the owner's
  audit view; all bilingual Italian/English, with loading, error and empty states.

### Key Entities

- **Account**: a person who can sign in, with role (owner, teacher, parent, student), confirmed
  flag, failed-attempt counter and lock window, optional second factor.
- **Invitation**: who invited whom, for which role, studio and students, expiry, status (pending,
  accepted, revoked, expired).
- **Consent record**: parent, children covered, notice version, given at, withdrawn at.
- **Second factor**: secret for the authenticator app (stored protected) and the hashed
  recovery codes with their used state.
- **Audit entry**: actor, action, target, studio, time, outcome, request identifier; append-only.
- **Student** (existing): gains the adult indicator and an optional link to a student account.
- **Lesson** (existing): its notes become encrypted.
- **Privacy notice version**: identifier and date of the notice text the consents refer to.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new owner goes from the sign-up page to an empty, usable studio in under 3
  minutes, including email confirmation.
- **SC-002**: A user who forgot their password is signed in again in under 2 minutes.
- **SC-003**: Comparing responses for registered and unregistered addresses on registration,
  reset and confirmation resend shows no difference in content.
- **SC-004**: 100% of endpoints have cross-scope tests for teacher, parent, student and studio,
  and all pass.
- **SC-005**: After 5 wrong passwords, the 6th attempt with the right password is refused for
  the lock window, in 100% of test runs.
- **SC-006**: A parent's export contains 100% of their and their children's records and 0
  records of other families, verified against seeded data.
- **SC-007**: After erasure, searching the data for the erased person's name and email returns
  0 results, and the studio's payment totals are unchanged.
- **SC-008**: Lesson notes are unreadable when the stored data is inspected without the key.
- **SC-009**: A secret committed on purpose in a test branch is detected and blocks the change.
- **SC-010**: Test coverage stays at or above 90% and every existing test keeps passing.

## Assumptions

- The legal basis for minors' data is the contract with the parent plus the parent's recorded
  consent; the texts are drafts and must be validated by a professional before real families
  use the product.
- The teacher may create a student record before the parent joins (the parent's agreement is
  gathered offline when lessons are arranged); the record holds only name and instrument until
  then.
- Retention periods (24 months after last activity, 10 years for payment records, 12 months
  for audit entries, 7 days for unconfirmed sign-ups) are reasonable defaults for an Italian
  music school and are to be confirmed during legal validation.
- Emails are sent through the existing email configuration: printed to the console locally,
  through the SMTP provider in production (owner's checklist, step 2).
- Encryption covers lesson notes, the only free text about a child today; progress notes and
  materials of phase 008 will follow the same rule.
- Mobile app screens for these flows come in a follow-up on `staging/mobile`; the API is shared.
- No SMS, no social sign-in, no single sign-on; the second factor is optional in this phase.
- Payments are not tested against the real provider by Claude; the owner runs those checks.
