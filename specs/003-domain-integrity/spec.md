# Feature Specification: Domain Integrity (Phase 2)

**Feature Branch**: `refactor/production-standards`
**Created**: 2026-11-06
**Status**: Draft
**Input**: User description: "Domain integrity (roadmap phase 2): no overlapping lessons,
explicit multi-tenancy, per-action/per-object permissions, explicit payment transitions,
OpenAPI contract polish, Italian study docs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A teacher's agenda can never contain overlapping lessons (Priority: P1)

A teacher (or the studio owner on their behalf) schedules lessons. Today nothing stops two
lessons for the same teacher at the same time, or one student booked with two teachers at
once; a double click or two people booking at the same moment creates a conflict nobody
notices until the student is at the door. After this feature the system refuses any lesson
that overlaps an active lesson of the same teacher or of the same student, even when two
requests arrive at the same instant, and tells the client clearly why.

**Why this priority**: scheduling is the core of the product; a double booking is the most
visible failure a teacher can experience.

**Independent Test**: create a lesson 10:00–10:45; try 10:30–11:00 for the same teacher
(refused), for the same student with another teacher (refused), 10:45–11:15 (accepted,
back-to-back); cancel the first one and retry 10:30 (accepted).

**Acceptance Scenarios**:

1. **Given** a scheduled lesson 10:00–10:45 for teacher T, **When** any lesson for T starting
   before 10:45 and ending after 10:00 is created or moved there, **Then** it is refused with
   a conflict response that says the slot is taken, and nothing is stored.
2. **Given** the same lesson for student S, **When** a lesson for S with a different teacher
   overlaps it, **Then** it is refused the same way.
3. **Given** a lesson ending at 10:45, **When** another starts exactly at 10:45, **Then** it
   is accepted.
4. **Given** a cancelled or no-show lesson, **When** a new lesson takes its slot, **Then** it
   is accepted.
5. **Given** two simultaneous requests for the same slot, **When** both are processed,
   **Then** exactly one succeeds and the other receives the conflict response.
6. **Given** existing clients, **When** they send and read the lesson length in minutes as
   before, **Then** they keep working unchanged.

---

### User Story 2 - The studio is the tenant, for everyone (Priority: P1)

Today a solo teacher has no studio, so the system decides what each user sees through
special cases per role. After this feature every teacher belongs to exactly one studio (a
solo teacher has a personal studio of one), every student belongs to a studio, and each
request works out once who the user is within which studio. What each role sees is
unchanged: a teacher sees their own students, an owner sees the whole studio, a parent sees
only their children.

**Why this priority**: a single, explicit tenant boundary is what keeps data isolation
correct as roles and features grow (phase 1 found two leaks in the ad-hoc approach).

**Independent Test**: after migrating existing data, every teacher and student has a
studio; all phase 1 isolation tests still pass; a studio owner never sees another studio's
data; per-request database work does not grow.

**Acceptance Scenarios**:

1. **Given** existing solo teachers, **When** the data is migrated, **Then** each gets a
   personal studio they own, and each student gets their teacher's studio.
2. **Given** any user, **When** they read or write, **Then** visibility is exactly as before
   (teacher: own students; owner: whole studio; parent: linked children).
3. **Given** a request, **When** it is processed, **Then** the user's studio and role are
   determined once and reused, not looked up repeatedly.
4. **Given** a teacher or student, **When** someone tries to leave them without a studio,
   **Then** the system refuses.

---

### User Story 3 - Who may do what is explicit, per action and per object (Priority: P2)

Parents only read. A teacher manages their own students and their lessons, packages, and
payments. A studio owner manages everything in their studio and can move a student to
another teacher of the same studio. A studio cannot exceed 10 teachers.

**Why this priority**: today permissions are "teachers write, everyone reads" plus
filtering; reassignment and the studio cap are product rules with no enforcement.

**Independent Test**: as owner, reassign a student to another teacher of the studio
(accepted) and to a teacher of another studio (refused); as teacher, try to reassign
(forbidden); add an 11th teacher to a studio (refused).

**Acceptance Scenarios**:

1. **Given** a studio owner, **When** they reassign a student to another teacher of their
   studio, **Then** the student's teacher changes; existing lessons keep their teacher.
2. **Given** a studio owner, **When** the target teacher belongs to another studio, **Then**
   the change is refused and nothing changes.
3. **Given** a teacher, **When** they try to reassign a student, **Then** they are
   forbidden.
4. **Given** a parent, **When** they attempt any write, **Then** they are forbidden
   (unchanged).
5. **Given** a studio with 10 teachers, **When** an 11th is added, **Then** it is refused.

---

### User Story 4 - Payment status follows clear rules (Priority: P2)

A payment is recorded as pending, paid, or overdue. Today any status can be changed into
any other, so a paid payment can silently go back to pending. After this feature only
these changes are possible: pending → paid, pending → overdue, overdue → paid. Paid is
final. A payment may still be recorded directly as paid (cash on the spot).

**Why this priority**: money records must be trustworthy; flagged as a property-level
authorization gap in the phase 1 security review.

**Independent Test**: try every pair of statuses on an existing payment; only the three
allowed changes succeed, the others are refused with a validation error naming the rule.

**Acceptance Scenarios**:

1. **Given** a pending payment, **When** it is marked paid or overdue, **Then** it succeeds.
2. **Given** an overdue payment, **When** it is marked paid, **Then** it succeeds.
3. **Given** a paid payment, **When** any status change is attempted, **Then** it is refused.
4. **Given** any payment, **When** a change is made without changing the status, **Then**
   it is accepted (other fields remain editable).

---

### User Story 5 - The API contract is documented and cannot drift (Priority: P2)

Client developers (web SPA, mobile app) rely on the published API description. After this
feature endpoints are grouped by domain, every error response a client must handle (invalid
input, unauthenticated, forbidden, not found, conflict, too many requests) is documented
with its shape, the description lives in the repository, and the pipeline fails when the
code and the published description disagree.

**Why this priority**: two clients consume this API; an undocumented or drifting contract
breaks them silently.

**Independent Test**: change a serializer field without regenerating the description; the
pipeline fails. Open the docs: each endpoint lists its error responses.

**Acceptance Scenarios**:

1. **Given** the API description, **When** a client developer reads it, **Then** endpoints
   are grouped by domain and each lists its possible error responses with a shared shape.
2. **Given** a code change that alters the contract, **When** the description in the
   repository is not updated, **Then** the pipeline fails.

---

### User Story 6 - The developer can study every decision of the phase (Priority: P2)

Same deliverable as phase 1: Italian concept docs (overlap constraints, multi-tenancy, DRF
permissions, API contracts), ADRs, glossary and interview Q&A updates, OWASP walk, docs
copied to the owner's Windows study folder.

**Independent Test**: each new concept doc stands alone, is 800–1500 words, follows the
required sections; the index and the Windows folder include them.

### Edge Cases

- A lesson moved (start or length changed) onto an occupied slot: refused like a new one.
- Completing a lesson that was cancelled, when its slot has since been taken: refused with
  the conflict response.
- Lessons across midnight or across a daylight-saving change: overlap is computed on real
  time, not on wall-clock dates.
- Reassigning a student whose future lessons would overlap the new teacher's agenda: not
  possible, because existing lessons keep their original teacher (assumption below).
- A parent whose children are in two different studios: still sees both (parents are not
  bound to one studio).
- A studio owner without a teacher profile: sees nothing (unchanged).
- Existing overlapping lessons at migration time: the migration stops and lists them instead
  of silently changing data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST refuse to store a lesson whose time interval overlaps an
  active (scheduled or completed) lesson of the same teacher, or of the same student.
  Intervals are half-open: a lesson ending at T does not overlap one starting at T.
- **FR-002**: The guarantee of FR-001 MUST hold under concurrent requests, enforced by the
  data store itself, not only by application checks.
- **FR-003**: An overlap MUST be answered with a conflict response (HTTP 409) whose message
  names the reason; cancelled and no-show lessons MUST NOT block a slot.
- **FR-004**: Clients MUST keep sending and receiving the lesson length in minutes; the
  lesson end time MAY additionally be exposed read-only.
- **FR-005**: Every teacher MUST belong to exactly one studio; existing solo teachers MUST be
  migrated to a personal studio they own.
- **FR-006**: Every student MUST belong to a studio, always equal to their teacher's studio.
- **FR-007**: The user's tenant context (studio, role, teacher or parent profile) MUST be
  resolved at most once per request and reused by all scoping.
- **FR-008**: Visibility rules from feature 002 MUST be preserved; all existing isolation
  tests MUST pass unchanged in intent.
- **FR-009**: Write permissions MUST be checked per action and per object: parents never
  write; teachers write only objects of their own students; owners write any object of
  their studio.
- **FR-010**: Only a studio owner MUST be able to reassign a student, and only to a teacher of
  the same studio; existing lessons keep their teacher.
- **FR-011**: A studio MUST NOT have more than 10 teachers.
- **FR-012**: Payment status changes MUST follow pending→paid, pending→overdue,
  overdue→paid; paid is final; invalid changes answer 400; creation may use any status.
- **FR-013**: The API description MUST group endpoints by domain, document error responses
  400/401/403/404/409/429 with a shared error shape, be committed to the repository, and the
  pipeline MUST fail when it is out of date.
- **FR-014**: The phase MUST deliver Italian study docs per the constitution, an OWASP API
  Top 10 walk, and copy the docs to the owner's Windows study folder.

### Key Entities

- **Studio** (tenant): now mandatory for every teacher and student; a solo teacher's studio
  has exactly one teacher, its owner.
- **Teacher**: belongs to exactly one studio.
- **Student**: gains its studio; its teacher can be changed by the studio owner.
- **Lesson**: gains a stored end time derived from start and length; subject to the
  no-overlap rule per teacher and per student.
- **Payment**: status becomes a small state machine.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 overlapping active lessons can exist, verified by a test that fires
  concurrent bookings for the same slot: exactly one succeeds in 100% of runs.
- **SC-002**: 100% of teachers and students have a studio after migration.
- **SC-003**: All phase 1 isolation and query-budget tests still pass; no main endpoint
  needs more database round-trips than in phase 1.
- **SC-004**: Every disallowed payment status change (6 of 9 pairs) is refused.
- **SC-005**: A deliberate contract change without updating the committed description fails
  the pipeline.
- **SC-006**: Test coverage stays ≥ 90%; four new concept docs of 800–1500 words each.

## Assumptions

- Active lesson statuses are `scheduled` and `completed`; `cancelled` and `no_show` free the
  slot. A completed lesson still occupied the slot in reality.
- The student-overlap rule applies across teachers and across studios of the same student
  record; a student record belongs to one studio, so in practice it is per studio.
- Reassignment changes only the student's teacher; existing lessons (past and future) keep
  their teacher. Moving future lessons is a separate feature if ever needed.
- The 10-teacher cap applies when a teacher joins a studio (admin, data migration, future
  invite flow); there is no public endpoint to add teachers in this phase.
- No production data exists yet (never deployed), so the migration to mandatory studios and
  the overlap constraint can be strict: they stop on inconsistent data rather than fixing it.
- Solo teachers keep the `teacher` role; owning their personal studio does not give them
  the `studio_owner` role (visibility is identical for a studio of one).
- The committed API description is generated from code; the pipeline compares a freshly
  generated one with the committed file.
