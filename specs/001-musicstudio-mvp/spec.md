# Feature Specification: MusicStudio MVP — Teacher & Parent Platform

**Feature Branch**: `web`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Build MusicStudio, a web platform for private music teachers and
small music studios (1-10 teachers) to manage students, recurring lessons, lesson packages,
payments, and parent communication — replacing the current patchwork of Calendly +
spreadsheets + WhatsApp/text messages." (full brief on file; see repo root prompt history)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Teacher runs their week and completes lessons (Priority: P1)

A teacher logs in and sees their week at a glance: scheduled lessons, the next few coming up,
and how many students they actively teach. After giving a lesson, they mark it complete and
optionally leave a short note — the student's remaining lesson count updates immediately so
the teacher always knows who is close to running out.

**Why this priority**: This is the daily-use loop that replaces the Calendly-plus-spreadsheet
habit. Without it, nothing else in the product gets touched regularly.

**Independent Test**: Log in as a teacher with at least one scheduled lesson today, mark it
complete with a note, and verify the student's package "lessons remaining" count decreases by
one and the lesson shows as completed with the note attached.

**Acceptance Scenarios**:

1. **Given** a teacher has lessons scheduled this week, **When** they open the dashboard,
   **Then** they see a weekly calendar of their lessons, their next three upcoming lessons
   highlighted, their count of pending payments, and their count of active students.
2. **Given** a scheduled lesson has occurred, **When** the teacher marks it "completed" and
   adds a progress note, **Then** the lesson's status changes to completed, the note is saved,
   and the linked package's remaining-lesson count decreases by exactly one.
3. **Given** a teacher marks a lesson as "no-show" or "cancelled", **When** they save that
   status, **Then** the package's remaining-lesson count does NOT change (only "completed"
   decrements it).
4. **Given** a lesson is already marked completed, **When** the teacher (or anyone) attempts to
   mark it completed again, **Then** the system does not decrement the package a second time.

---

### User Story 2 - Teacher manages students, packages, and payments (Priority: P1)

A teacher keeps a roster of their students, each with an active lesson package and payment
status visible at a glance. They can open any student to see lesson history, attendance, and
progress notes, and they can register a payment (cash, bank transfer, or manual entry) against
a student's package.

**Why this priority**: Packages and payments are the money side of the business this product
replaces spreadsheets for; a teacher who can't trust this data won't adopt the tool.

**Independent Test**: Open the roster, confirm each student shows their active package and
payment status, open one student's detail view, confirm lesson history and current package are
visible, then register a manual payment and confirm its status appears in the payments list.

**Acceptance Scenarios**:

1. **Given** a teacher has students with different package/payment states, **When** they view
   the roster, **Then** each row shows the student, their active package, lessons remaining,
   and current payment status.
2. **Given** a teacher opens a student's detail view, **When** the page loads, **Then** they see
   that student's lesson history with attendance status, any progress notes per lesson, and the
   current package with its renewal status.
3. **Given** a teacher wants to record money received, **When** they use the "register payment"
   action with an amount, date, and method, **Then** a payment record is created and appears in
   the payments list with the correct status.
4. **Given** a student's package has 1-2 lessons remaining, **When** the teacher views the
   roster or dashboard, **Then** that student is visibly flagged as running low.

---

### User Story 3 - Parent checks on their child without seeing anyone else's data (Priority: P2)

A parent (or adult student) logs into their own restricted portal and sees only their own
child's (or their own) upcoming lessons, attendance history, and payment status — nothing
belonging to any other family.

**Why this priority**: This is what actually replaces the WhatsApp/text back-and-forth for
status questions, and it is the feature most exposed to a trust failure if scoped wrong — but
the product is usable by the teacher alone without it, so it follows the P1 teacher-side loop.

**Independent Test**: Log in as a parent linked to one student, confirm only that student's
data is visible anywhere in the portal, and confirm attempting to access another family's
student (by any means available in the UI, including direct navigation) is denied.

**Acceptance Scenarios**:

1. **Given** a parent account linked to one student, **When** they log in, **Then** they see
   that student's upcoming lessons, attendance history, and payment status, with no edit
   controls anywhere.
2. **Given** a parent linked to multiple students (siblings), **When** they log in, **Then**
   they can see and switch between only their own linked students.
3. **Given** a parent is logged in, **When** they attempt to view or navigate to a student they
   are not linked to, **Then** access is denied and no data about that student is revealed.
4. **Given** a teacher marks a lesson completed with a progress note, **When** the linked
   parent views that lesson, **Then** the updated attendance and note appear without the parent
   taking any action.

---

### User Story 4 - The system reminds people so no one has to chase them (Priority: P3)

Instead of a teacher texting reminders by hand, the system automatically reminds a parent
about a lesson coming up tomorrow, and separately warns the teacher when a student is about to
run out of lessons in their package.

**Why this priority**: High value but not required to demonstrate the core record-keeping loop
working; it automates a task the earlier stories already made possible.

**Independent Test**: With a lesson scheduled ~24h out, confirm a reminder is queued/sent to
the linked parent; with a package at 1-2 lessons remaining, confirm the teacher sees a low-
package warning without a parent reminder for that condition.

**Acceptance Scenarios**:

1. **Given** a lesson is scheduled approximately 24 hours from now, **When** the reminder job
   runs, **Then** a reminder is sent (or demonstrably queued) to the lesson's linked parent
   exactly once for that lesson.
2. **Given** a student's package drops to 1-2 lessons remaining after a completion, **When**
   the teacher next views their dashboard, **Then** they see a warning for that student.
3. **Given** a lesson is cancelled before the reminder fires, **When** the reminder job runs,
   **Then** no reminder is sent for that lesson.

### Edge Cases

- A student has no active package and a lesson is marked completed: the system MUST NOT
  decrement a package that doesn't exist, and MUST still surface the completion (flag the
  student as needing a new package).
- A package's remaining-lesson count is already zero and a lesson tied to it is marked
  completed: the system MUST NOT go negative; the studio owner/teacher sees the same "needs
  renewal" state rather than a broken count.
- A parent account has no linked students (e.g. link removed): the portal shows an empty,
  clearly-explained state rather than an error.
- A studio owner has multiple teachers: each teacher sees only their own students/lessons
  unless the studio owner's own dashboard aggregates across their studio.
- A payment is registered against a package that doesn't match the student it's for: rejected
  as invalid input.
- Two lessons for the same teacher overlap in time: the system allows it to be created (real
  studios double-book for trials/overlaps sometimes) but visibly flags the overlap on the
  calendar rather than silently hiding it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support three account roles — teacher, studio owner, and parent —
  each seeing a UI scoped to that role.
- **FR-002**: System MUST let a teacher view a weekly calendar of their own scheduled lessons,
  with their next three upcoming lessons highlighted.
- **FR-003**: System MUST let a teacher view counts of their pending payments and active
  students on their dashboard.
- **FR-004**: System MUST let a teacher view a roster of their students showing active
  package, lessons remaining, and payment status.
- **FR-005**: System MUST let a teacher open a student detail view showing lesson history with
  attendance, per-lesson progress notes, and current package/renewal status.
- **FR-006**: System MUST let a teacher mark a scheduled lesson's status as completed,
  cancelled, or no-show, and optionally attach a short progress note visible to the linked
  parent.
- **FR-007**: System MUST decrement a student's active package's remaining-lesson count by
  exactly one when, and only when, a lesson linked to that package transitions to "completed"
  for the first time.
- **FR-008**: System MUST let a teacher manually register a payment (amount, date, method:
  cash / bank transfer / manual entry) and track its status (paid, pending, overdue).
- **FR-009**: System MUST let a teacher view a list of payments with their status.
- **FR-010**: System MUST restrict a parent account to read-only access scoped to their own
  linked student(s): upcoming lessons, attendance history, and payment status — with no access,
  through any interface, to another family's data.
- **FR-011**: System MUST send (or queue) a reminder to a lesson's linked parent approximately
  24 hours before that lesson's scheduled time, at most once per lesson.
- **FR-012**: System MUST warn the teacher when a student's package reaches 1-2 remaining
  lessons.
- **FR-013**: System MUST support a studio owner overseeing multiple teachers (1-10) under one
  studio; a solo teacher MUST be able to use the system without belonging to any studio.
- **FR-014**: System MUST support all product text in both English and Italian, with a
  user-facing way to switch language at any time.
- **FR-015**: System MUST support a user-facing light/dark appearance toggle.
- **FR-016**: System MUST prevent a parent account from creating, editing, or deleting any
  record (lessons, packages, payments, students) — parent access is read-only everywhere.

### Key Entities

- **User**: base account with a role (teacher, studio_owner, parent) and authentication
  credentials.
- **Teacher**: a teacher's profile, optionally belonging to a Studio; a solo teacher has no
  Studio.
- **Studio**: groups 1-10 teachers under one studio owner.
- **Student**: a person taking lessons — name, instrument, the teacher they study with, and
  (for minors) the parent account linked to them.
- **ParentAccount**: linked to one or more Students; has read-only visibility into exactly
  those students' data.
- **Package**: a bundle of lessons a Student purchased — total lessons, lessons remaining,
  purchase date, price, and renewal/expiry state.
- **Lesson**: a scheduled date/time for a Student with a Teacher, a status (scheduled,
  completed, cancelled, no-show), and an optional progress note.
- **Payment**: an amount, date, method, and status (paid, pending, overdue), tied to a Package
  or standalone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A teacher can go from login to seeing their current week's schedule in under 10
  seconds of navigation (no more than 2 screens).
- **SC-002**: Marking a lesson complete and having the student's remaining-lesson count reflect
  it takes one action (no multi-step confirmation flow) and is reflected immediately on
  screen.
- **SC-003**: A parent, logging in independently from the teacher, sees their child's updated
  attendance and payment status without contacting the teacher, 100% of the time when the
  teacher has made the corresponding update.
- **SC-004**: 0% of cross-family data exposure in parent accounts: a parent account can never
  retrieve another family's student, lesson, package, or payment data, under any tested access
  path.
- **SC-005**: A reminder for an upcoming lesson is demonstrably queued or sent within the
  24-hour-before window for 100% of scheduled, non-cancelled lessons in testing.
- **SC-006**: A studio owner managing up to 10 teachers can see the whole studio's activity
  without any teacher seeing another teacher's students by default.
- **SC-007**: All user-facing text is available in both English and Italian with no
  untranslated strings visible in either language mode.

## Assumptions

- "Minor" students are represented by requiring a linked ParentAccount for portal access;
  adult students may act as their own "parent" account (self-serve portal) — the data model
  does not hard-distinguish minor vs. adult beyond who holds the login.
- A package's "expiry/renewal logic" for MVP means: a package is "active" while lessons
  remain and it hasn't passed an optional expiry date; renewal is a manual action (buying a
  new package), not automatic re-billing (no payment gateway in MVP).
- "Studio owner" is a superset role that can see all teachers/students/payments within their
  studio; a plain "teacher" without owner rights only sees their own.
- Reminders and low-package warnings are the only automated notifications in MVP; no SMS,
  push notifications, or in-app chat (WhatsApp replacement is achieved by parents no longer
  needing to ask for status, not by rebuilding messaging).
- Overlapping lessons for the same teacher are allowed but flagged, not blocked — studios
  sometimes intentionally double-book (trials, makeups).
- No payment gateway, native mobile app, video lessons, file sharing, recital/event planning,
  or languages beyond English/Italian are in scope for this feature (see project constitution,
  Principle IV).
