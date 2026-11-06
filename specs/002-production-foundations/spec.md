# Feature Specification: Production Foundations (Phase 1)

**Feature Branch**: `refactor/production-standards`
**Created**: 2026-11-06
**Status**: Draft
**Input**: User description: "Production foundations (phase 1): bring the existing MusicStudio
backend to production standard without changing product behaviour beyond fixing defects."
Source audit: `docs/learning/audit-iniziale.md` (gaps G1–G18).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A teacher can only ever write to their own students (Priority: P1)

A teacher (or studio owner) records lessons, packages, and payments. Today a teacher can
attach a lesson or a payment to a student who belongs to a different teacher by sending that
student's identifier. After this feature, any attempt to write data for a student or package
outside the teacher's own scope is rejected, and nothing is stored.

**Why this priority**: it is a verified data-integrity and privacy breach between tenants
(audit G1). Every other improvement is worthless if one customer can tamper with another's
records.

**Independent Test**: as teacher A, try to create a lesson, a payment, and a package for
teacher B's student, and try to move one of A's lessons onto B's student; every attempt is
refused and B's data is unchanged.

**Acceptance Scenarios**:

1. **Given** teacher A and a student of teacher B, **When** A creates a lesson, payment, or
   package for that student, **Then** the request is refused as invalid input and no record
   is created.
2. **Given** a lesson of teacher A, **When** A changes its student to a student of teacher B,
   **Then** the change is refused.
3. **Given** a studio owner, **When** they write data for any student of a teacher in their
   studio, **Then** it succeeds; for a student outside the studio it is refused.
4. **Given** a parent, **When** they attempt any write, **Then** it is refused (unchanged
   behaviour).

---

### User Story 2 - Lists and the dashboard stay fast as a studio grows (Priority: P1)

A teacher opens the student roster or the weekly dashboard. Today the work done by the
system grows with every student shown (two extra database round-trips per student on the
roster, one per student on the dashboard). After this feature the amount of work per page is
constant regardless of how many students are listed.

**Why this priority**: the roster and dashboard are the most-used screens; the cost grows
linearly with the customer's success (audit G2).

**Independent Test**: load the roster and dashboard with 1 and with 25 students; the number
of database round-trips is identical, and automated tests fail if it ever grows again.

**Acceptance Scenarios**:

1. **Given** a teacher with N students, **When** they load the roster, **Then** the number
   of database round-trips is a fixed number independent of N.
2. **Given** the same, **When** they load the dashboard, lessons, packages, or payments
   lists, **Then** the same holds.
3. **Given** the roster, **When** it is displayed, **Then** each student's current package
   and latest payment status are identical to what was shown before the change.

---

### User Story 3 - Correct behaviour on edge inputs (Priority: P2)

A teacher creates a lesson package by stating only how many lessons it contains, as the API
contract always promised; today this fails unless the remaining count is also sent. A client
sends a malformed week to the lessons list; today the server crashes with an internal error.
A studio-owner account that has no teacher profile opens the studio page; today it crashes.

**Why this priority**: defects found in the audit (G4, G5, G15); each is small but visible.

**Independent Test**: create a package with only the total; request the lessons list with an
invalid week; open the studio page as a misconfigured owner. All return clear, non-crash
responses.

**Acceptance Scenarios**:

1. **Given** a teacher, **When** they create a package with a total of 8 lessons and no
   remaining count, **Then** the package is created with 8 lessons remaining.
2. **Given** an existing package, **When** a client tries to set its remaining count
   directly, **Then** the value is ignored (only lesson completion changes it).
3. **Given** any user, **When** they request lessons for an invalid week value, **Then** they
   receive a validation error, not a server error.
4. **Given** a studio owner without a teacher profile, **When** they open the studio page,
   **Then** they receive "not found", not a server error.

---

### User Story 4 - An operator can deploy, observe, and recover the system (Priority: P1)

The person running MusicStudio deploys it on their own server through Coolify, using one
production definition. They need: every component to report whether it is healthy; the
application to refuse to start with missing or unsafe production configuration; the
database to be backed up automatically on a schedule with retention; no component exposed
on a public port except through the reverse proxy; no dependency on AWS.

**Why this priority**: without it the system cannot be run responsibly in production
(audit G7, G8, G9, G10).

**Independent Test**: start the production definition locally with required variables
missing (it refuses), then with them set (every component becomes healthy, the liveness and
readiness checks answer, a backup file appears on schedule).

**Acceptance Scenarios**:

1. **Given** the production definition, **When** a required secret is missing, **Then**
   deployment or start-up fails with a message naming the missing variable.
2. **Given** a running stack, **When** the health checks are queried, **Then** liveness
   answers without touching dependencies and readiness reports database and broker status,
   returning a failure status when either is down.
3. **Given** a running stack, **When** the backup schedule elapses, **Then** a compressed
   database dump exists and old dumps beyond the retention window are removed.
4. **Given** the repository, **When** it is searched for AWS services or SDKs, **Then** none
   are referenced outside historical notes.

---

### User Story 5 - Login cannot be brute-forced (Priority: P2)

An attacker tries thousands of passwords against the login endpoint. After this feature,
repeated attempts from the same client are slowed down with a "too many requests" answer.

**Why this priority**: OWASP API4 (unrestricted resource consumption) and account takeover
(audit G11).

**Independent Test**: exceed the login attempt limit; subsequent attempts are refused until
the window resets.

**Acceptance Scenarios**:

1. **Given** a client, **When** it exceeds the login attempt limit within the window,
   **Then** further attempts receive "too many requests".
2. **Given** authenticated API use, **When** a user stays within normal usage, **Then** they
   are never throttled.

---

### User Story 6 - Parents never get the same reminder twice (Priority: P2)

Parents receive an email reminder about 24 hours before each lesson. If two reminder runs
overlap, or a run is interrupted, a parent can today receive the same reminder twice. After
this feature each lesson's reminder is sent at most once.

**Why this priority**: duplicate emails look unprofessional and erode trust (audit G13).

**Independent Test**: run two reminder sweeps over the same window; each parent receives
exactly one email per lesson.

**Acceptance Scenarios**:

1. **Given** a lesson in the reminder window, **When** two sweeps run, **Then** exactly one
   reminder per linked parent is sent.
2. **Given** a cancelled lesson in the window, **When** a sweep runs, **Then** no reminder is
   sent (unchanged).

---

### User Story 7 - The team cannot merge code that breaks the standards (Priority: P1)

A developer opens a change. An automated pipeline checks style, static types, that database
migrations are in sync, and runs the full test suite with coverage against the same database
engine used in production. A failing check blocks the merge. The same checks run locally
before each commit.

**Why this priority**: standards not enforced by a machine erode (audit G6; Constitution VII).

**Independent Test**: push a change with a lint error, a type error, a missing migration, or a
failing test; the pipeline fails for each.

**Acceptance Scenarios**:

1. **Given** a push or pull request, **When** the pipeline runs, **Then** lint, format, type,
   migration, and test checks all execute and any failure marks the pipeline failed.
2. **Given** a clean change, **When** the pipeline runs, **Then** it passes and reports
   coverage at or above the agreed threshold.

---

### User Story 8 - The developer can study every decision (Priority: P2)

The project owner studies the system to defend it at an interview. Every phase produces, in
Italian, an index, an architecture overview, ADRs, one document per concept, a glossary, and
interview questions with model answers.

**Why this priority**: explicit deliverable of the project (Constitution VIII).

**Independent Test**: each concept document stands alone, is 800–1500 words, and follows the
required section structure; the index lists every document with a reading order.

**Acceptance Scenarios**:

1. **Given** the `docs/learning/` folder, **When** the owner opens the index, **Then** every
   document is listed with a one-line description and a recommended reading order.
2. **Given** any concept document, **When** it is loaded alone, **Then** it is understandable
   without the others and contains all required sections.

### Edge Cases

- A studio owner whose studio has no other teachers: scoping still works (they see their own
  students only).
- A payment referencing a package of a different student of the same teacher: refused
  (unchanged rule, now enforced in one place).
- A package whose remaining count is 0: lesson completion never makes it negative
  (unchanged).
- Readiness when the broker is down but the database is up: reported as not ready.
- Backup when the database is temporarily unavailable: the failure is visible in the backup
  component's health, and the next scheduled run retries.
- Reminder run interrupted after claiming a lesson but before sending: that reminder is lost
  rather than duplicated (accepted trade-off; documented).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST reject any create or update whose referenced student or
  package lies outside the requesting user's scope, returning a validation error and storing
  nothing.
- **FR-002**: The system MUST serve the roster, lessons, packages, payments, and dashboard
  endpoints with a number of database round-trips that does not depend on the number of rows
  returned; automated tests MUST pin these numbers.
- **FR-003**: The system MUST keep business rules (lesson completion and cancellation,
  package creation, lesson defaults, payment consistency, dashboard aggregation, reminders) in
  a dedicated service/selector layer, independent of the HTTP layer.
- **FR-004**: The system MUST create a package with remaining lessons equal to its total
  when no remaining count is given, and MUST NOT let clients set the remaining count directly.
- **FR-005**: The system MUST answer malformed query parameters with a validation error
  (HTTP 400), never an internal error.
- **FR-006**: The system MUST answer the studio endpoints with "not found" when the owner
  has no teacher profile or studio.
- **FR-007**: The system MUST expose an unauthenticated liveness check that does not touch
  dependencies, and a readiness check that verifies database and broker connectivity and
  returns a failure status when either is unavailable.
- **FR-008**: The system MUST load all environment-specific configuration from environment
  variables, provide separate development, test, and production profiles, and in production
  refuse to start when required values are missing.
- **FR-009**: The production profile MUST trust the reverse proxy's TLS indication, enforce
  HTTPS, use secure cookies, and accept the configured public origins for CSRF.
- **FR-010**: The login endpoint MUST be rate-limited per client; general API use MUST be
  rate-limited per user with limits that normal use never reaches.
- **FR-011**: The reminder sweep MUST send each lesson's reminder at most once, even when
  sweeps overlap.
- **FR-012**: The system MUST run on the current long-term-support release of its web
  framework.
- **FR-013**: The hot queries (lessons by teacher and time, lessons by status and time for
  reminders, payments by student and date, payments by status, packages by student and
  purchase date) MUST be supported by indexes.
- **FR-014**: The repository MUST provide a development stack definition and a Coolify
  production stack definition; in production no service publishes a host port, every
  service declares a health check, required secrets are mandatory variables, and the
  database is backed up on a schedule with retention.
- **FR-015**: The repository MUST NOT reference AWS services, SDKs, or deployment docs,
  except in historical notes of feature 001.
- **FR-016**: A CI pipeline MUST run lint, format check, static type check, migration
  consistency check, and the test suite with coverage on every push and pull request; any
  failure MUST fail the pipeline. Local pre-commit hooks MUST run the same fast checks.
- **FR-017**: The existing frontend code MUST NOT be modified or deleted; the development
  stack MUST be startable without it.
- **FR-018**: Demo seeding with well-known passwords MUST refuse to run in production unless
  explicitly forced.
- **FR-019**: The phase MUST deliver the Italian study documentation set defined in the
  constitution, plus a roadmap for phases 2–5 in the plan.

### Key Entities

No new business entities. Existing entities (User, Studio, Teacher, Student, ParentAccount,
Package, Lesson, Payment) gain indexes only; Package's remaining count becomes system-managed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of write endpoints touching tenant data have an automated test proving a
  cross-tenant write is refused.
- **SC-002**: Database round-trips for the roster and dashboard are identical for 1 and 25
  students (previously 4→22 and 5→14 for 1→10 students).
- **SC-003**: Zero server errors from the known malformed inputs (invalid week, misconfigured
  owner, package without remaining count).
- **SC-004**: The full test suite passes, with line coverage of application code ≥ 90%.
- **SC-005**: Every service in the production stack reports healthy within 2 minutes of
  start-up on a clean server.
- **SC-006**: A database backup is produced at least daily and kept for at least 7 days.
- **SC-007**: A deliberately broken change (lint, type, migration, or test) fails CI in 100%
  of cases.
- **SC-008**: Every concept document is 800–1500 words and contains all required sections.

## Assumptions

- The starting point is the Django backend at commit `4be062d` (ADR-001); the `web` and `app`
  branches are untouched.
- Coolify terminates TLS at its proxy and forwards `X-Forwarded-Proto`.
- No `main` branch exists yet; branch protection ("CI blocks merge") is enabled by the
  repository owner on GitHub once `main` is created — it cannot be set from code.
- At-most-once delivery for reminders is preferred over at-least-once (a missed reminder is
  less harmful than spam); full task idempotency is a phase 3 topic.
- Login rate limit: 5 attempts per minute per client; authenticated users 1000 requests/hour;
  anonymous 100/hour. Reasonable defaults, configurable by environment.
- Backups: daily, 7 daily / 4 weekly / 6 monthly retained, on a volume of the Coolify host;
  off-site copy is a phase 4 topic.
- Phases 2–5 are roadmap only in this feature; they are specified separately when started.
