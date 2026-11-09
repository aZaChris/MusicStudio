# Feature Specification: Mobile App on the Django API (Phase 1, Parity)

**Feature Branch**: `refactor/mobile`
**Created**: 2026-11-09
**Status**: Draft
**Input**: User description: "Mobile refactor phase 1 — rewire the Expo app onto the Django
REST API with functional parity with branch `app`; fix the audit issues; generated types,
tests, CI, Italian study docs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign in, stay signed in, sign out for real (Priority: P1)

A teacher, studio owner or parent opens the app and signs in with email and password. They
stay signed in while they use the app, even across long sessions, without being thrown back
to the login screen. When they sign out, the session ends on the server too, and the next
person using the same phone sees nothing of theirs.

**Why this priority**: nothing else works without it, and today's app cannot sign in to the
Django backend at all.

**Independent Test**: sign in as each role and land on the right home; leave the app idle
past the short session window and keep using it without a new login; sign out and verify
that the old session cannot be resumed and that no previous data is visible.

**Acceptance Scenarios**:

1. **Given** valid credentials, **When** the user signs in, **Then** teachers and owners land
   on the teacher home and parents on the parent portal.
2. **Given** wrong credentials, **When** the user signs in, **Then** a clear "invalid
   credentials" message appears and nothing is stored.
3. **Given** a signed-in user whose short-lived access has expired, **When** they open any
   screen, **Then** the app renews the session silently and the screen loads.
4. **Given** several screens loading at the same moment with expired access, **When** the
   session is renewed, **Then** it is renewed once, not once per screen.
5. **Given** the session can no longer be renewed (revoked or expired), **When** any request
   fails for that reason, **Then** the user is taken to the login screen with a short
   explanation.
6. **Given** any role, **When** the user taps "Log out", **Then** the server ends the session,
   local credentials and cached data are erased, and the login screen appears; if the server
   cannot be reached, local data is erased anyway.
7. **Given** a stored session at startup, **When** the app opens, **Then** it re-checks the
   user with the server before showing role-specific screens.

---

### User Story 2 - Teacher home and completing a lesson (Priority: P1)

A teacher or owner sees a greeting, how many active students they have, how many payments
are pending, the upcoming lessons and a warning for students whose package is running low.
Tapping a scheduled lesson lets them mark it completed with an optional progress note.

**Why this priority**: it is the screen opened several times a day, and completing a lesson
is the action that moves money (the package counter).

**Independent Test**: with seeded data, the home shows the same counts the server reports;
completing a lesson updates the home and the student's remaining lessons.

**Acceptance Scenarios**:

1. **Given** a teacher with students and lessons, **When** the home opens, **Then** counts,
   upcoming lessons (student name and local date/time) and low-package names match the
   server.
2. **Given** a scheduled lesson, **When** the teacher completes it with a note, **Then** the
   lesson disappears from upcoming and the student's remaining lessons decrease by one.
3. **Given** the server refuses the completion (e.g. already completed), **When** it answers,
   **Then** the teacher sees the server's reason and the dialog stays open.
4. **Given** no upcoming lessons, **When** the home opens, **Then** an empty-state message is
   shown instead of a blank area.

---

### User Story 3 - Roster and student detail (Priority: P2)

A teacher or owner sees the list of all their active students, with instrument, remaining
lessons, a low-package badge and payment status. Opening a student shows the package and the
full lesson history with status and notes.

**Why this priority**: daily reference screen; today it silently shows only the first page.

**Independent Test**: with more students than one server page, the list shows all of them;
the detail of a student shows every lesson of that student.

**Acceptance Scenarios**:

1. **Given** 40 active students, **When** the roster opens, **Then** all 40 appear (loaded
   progressively while scrolling is acceptable).
2. **Given** a student, **When** the teacher opens the detail, **Then** package status and
   lesson history appear with translated statuses.
3. **Given** a student id that is not visible to the user, **When** the detail opens, **Then**
   a "not found" state appears, not a crash or an empty screen.

---

### User Story 4 - Payments (Priority: P2)

A teacher or owner sees the list of payments with student, amount, translated method and
status, and registers a manual payment (cash, bank transfer or manual entry) for a student,
dated today in the local time zone.

**Why this priority**: money; today the date can be yesterday after midnight and errors are
invisible.

**Independent Test**: register a payment just after midnight local time and check the date;
force a server validation error and check that it is shown.

**Acceptance Scenarios**:

1. **Given** a chosen student, an amount and a method, **When** the teacher registers the
   payment, **Then** it appears in the list with today's local date and the form resets.
2. **Given** the server rejects the payment (e.g. invalid amount), **When** it answers,
   **Then** the reason is shown next to the form and nothing is cleared.
3. **Given** more students than one server page, **When** choosing the student, **Then** every
   active student can be chosen.

---

### User Story 5 - Parent portal (Priority: P2)

A parent picks one of their children and sees, read-only, the lessons with attendance and
notes, and the payment status. A parent with one child sees that child directly.

**Why this priority**: the reason parents install the app; must stay read-only.

**Independent Test**: sign in as a parent with two children; switch between them; verify
that no edit action is offered and that only their own children appear.

**Acceptance Scenarios**:

1. **Given** a parent with two linked children, **When** the portal opens, **Then** both can
   be selected and each shows only its own lessons and payments.
2. **Given** a parent with no linked children, **When** the portal opens, **Then** a clear
   "no students linked" message appears.
3. **Given** the parent portal, **When** it is displayed, **Then** no action that changes data
   is available.

---

### User Story 6 - Quality and study material (Priority: P3)

Every change is checked automatically (types, lint, tests, contract), and the refactor is
documented in Italian for study, like the backend.

**Why this priority**: keeps the app correct over time; the study docs are a deliverable.

**Independent Test**: break the contract on purpose and see the check fail; run the full gate
locally and in CI.

**Acceptance Scenarios**:

1. **Given** the backend contract changes, **When** the check runs, **Then** it fails until the
   app's copy is refreshed and the types regenerated.
2. **Given** a push to the branch, **When** CI runs, **Then** types, lint, tests and contract
   check all run and must pass.

### Edge Cases

- No network at sign-in or during use: a clear offline/unreachable message, not an endless
  spinner; the user is not signed out because of it.
- The server answers "forbidden" (e.g. a parent somehow reaching a teacher screen): message,
  no retry, no crash.
- Session renewal fails while a payment is being registered: the user is sent to login and the
  payment is not reported as saved.
- Two users share a phone: after sign-out and a new sign-in, nothing of the first user is
  visible, even briefly.
- The user's role changed on the server since the last launch: the startup re-check routes
  them to the right area.
- Device language other than Italian or English: English is used.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to sign in with email and password against the Django API.
- **FR-002**: The app MUST renew an expired session automatically and transparently, with at
  most one renewal in flight at a time.
- **FR-003**: When the session cannot be renewed, the app MUST return to the login screen and
  explain why.
- **FR-004**: Every role MUST be able to sign out; sign-out MUST end the session on the server
  and erase local credentials and all cached data, even if the server is unreachable.
- **FR-005**: At startup with a stored session, the app MUST re-verify the user and role with
  the server before showing role-specific screens.
- **FR-006**: Teachers and owners MUST see the home with greeting, active-students count,
  pending-payments count, upcoming lessons and low-package students.
- **FR-007**: Teachers and owners MUST be able to complete a scheduled lesson with an optional
  note; the home and roster MUST reflect the change.
- **FR-008**: The roster MUST include every active student, beyond the server's page size.
- **FR-009**: The student detail MUST show the active package and the full lesson history.
- **FR-010**: Teachers and owners MUST be able to list payments and register a manual payment
  dated with the device's local date.
- **FR-011**: Parents MUST see, read-only, lessons, attendance and payment status per child,
  with a child selector when they have more than one.
- **FR-012**: Server refusals MUST be shown to the user in their language: invalid input and
  conflicts with the server's reason, forbidden and not-found with a clear message; requests
  refused by the server MUST NOT be retried automatically.
- **FR-013**: Every value coming from the server as a code (lesson status, payment status,
  payment method, package status) MUST be shown translated.
- **FR-014**: Interactive elements MUST be announced correctly by screen readers (role and
  label).
- **FR-015**: Data shapes used by the app MUST come from the backend's published contract,
  and a check MUST detect when the app's copy of the contract is out of date.
- **FR-016**: Types, lint, tests and the contract check MUST run automatically on every push.
- **FR-017**: Italian study documentation (audit, ADRs, concept docs, glossary, interview
  questions, index) MUST be produced for this phase.

### Key Entities

- **Session**: the signed-in user's credentials (short-lived access, renewable refresh) and
  the verified user (id, email, role, language, teacher or parent profile).
- **Student, Package, Lesson, Payment, Dashboard**: as published by the backend contract; the
  app holds no business rules about them beyond display.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of parity flows of the `app` branch (sign-in, home, complete lesson, roster,
  student detail, payments, parent portal) work against the Django backend.
- **SC-002**: A user can keep using the app for over an hour without seeing the login screen,
  while the server's access window is 15 minutes.
- **SC-003**: After sign-out, 0 screens show data of the previous user, and the previous
  session cannot be resumed.
- **SC-004**: A payment registered between 00:00 and 01:00 local time carries today's date in
  100% of cases.
- **SC-005**: Every server refusal in the parity flows produces a visible, translated message;
  0 silent failures in the tested scenarios.
- **SC-006**: Changing the backend contract without refreshing the app's copy fails the
  automatic check every time.

## Assumptions

- The backend is the Django API on branch `refactor/production-standards`, reachable at a
  configurable base address; locally it runs from the main checkout.
- The app keeps running in Expo Go; no custom native build is introduced in this phase.
- Verification in this environment uses automated tests and the web build against a local
  backend; there is no iOS/Android emulator. A real-device check is an owner task.
- Online payment (Stripe checkout from the parent portal) is out of scope: not in `app`, so not
  parity.
- Student creation, lesson scheduling and studio management are out of scope: they are not in
  the `app` branch either.
- The greeting uses the part of the email before "@", as in the `app` branch, because the
  backend user has no display name.
