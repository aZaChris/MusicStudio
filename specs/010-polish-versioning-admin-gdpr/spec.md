# Feature Specification: Polish — API Versioning, Admin Hardening, Complete Data Export, Portfolio Write-up

**Feature Branch**: `010-polish-versioning-admin-gdpr`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "Phase 5 Polish: API versioning and deprecation policy, Django admin
hardening, GDPR data export hardening/completeness check, and the portfolio write-up
(README/case study). Backend on main; study docs in Italian."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safe evolution of the public API (Priority: P1)

The mobile app and the web portal are installed on devices the owner does not control. When the
backend changes, an old app must keep working for a known period, and its developers must be told
well in advance what will go away. Today the API lives under `/api/v1/` and nothing says what
"v1" promises, how a change is announced, or how long an old behaviour survives.

**Why this priority**: the mobile app already reads the contract from `main`; the first
breaking change without a policy would break installed apps. It is also the part of "polish" a
reviewer of a backend portfolio looks at first.

**Independent Test**: mark one existing endpoint as deprecated in a test; verify that its
responses carry the deprecation and removal-date signals, that the contract marks it
deprecated, and that every other endpoint is unchanged.

**Acceptance Scenarios**:

1. **Given** an endpoint declared deprecated with a removal date, **When** a client calls it,
   **Then** the response still works exactly as before and carries machine-readable deprecation
   information including the removal date.
2. **Given** the published contract, **When** a developer reads it, **Then** deprecated
   operations are visibly marked as deprecated.
3. **Given** a change that removes or renames a field of a published response, **When** the
   automated checks run, **Then** they fail unless the change is registered as a breaking change
   with a new API version.
4. **Given** the written policy, **When** a mobile developer reads it, **Then** it states what
   counts as breaking, the minimum notice period before removal, and where deprecations are
   announced.
5. **Given** a deprecated endpoint, **When** its removal date is within 30 days (or passed)
   and it is still in the code, **Then** a scheduled check turns red and tells the owner to
   remove it or to extend the date with a written reason, so the date cannot be forgotten.
6. **Given** a deprecated endpoint, **When** the owner opens the deprecation register,
   **Then** it shows for each one: the removal date, days left, the replacement, the link to
   its migration report, and how many calls it received in the last 30 days.
7. **Given** the decision to deprecate something, **When** the owner starts from the migration
   report template, **Then** it guides them through what changes, who is affected (web portal,
   mobile app, other clients), old and new request/response side by side, the steps for each
   client, a test checklist, the timeline and the rollback.

---

### User Story 2 - Operator-only admin that cannot be abused (Priority: P2)

The Django admin is the operator's tool (unlock an account, revoke sessions, inspect data). It
holds every studio's data, so a stolen operator password or a careless click is the worst
possible incident. Today the admin works but is the Django default with a few actions.

**Why this priority**: it is the single place that bypasses the per-studio isolation; hardening
it closes the largest remaining security gap after phase 7.

**Independent Test**: sign in as a studio owner or teacher (not an operator) and try the admin
URL; sign in as an operator without two-step verification and try again; try to edit or delete a
payment, an audit entry, or a receipt from the admin.

**Acceptance Scenarios**:

1. **Given** a studio owner or teacher account, **When** it opens the admin, **Then** access is
   denied.
2. **Given** an operator account without verified two-step verification, **When** it opens the
   admin in production, **Then** access is denied until verification is done.
3. **Given** records that are final by design (collected payments, reversal entries, receipts,
   audit entries), **When** an operator opens them in the admin, **Then** they are read-only:
   no edit, no delete, no bulk delete.
4. **Given** any state-changing action in the admin, **When** an operator performs it, **Then**
   an audit entry records who, what and when.
5. **Given** the production deployment, **When** the admin address is requested from a client
   outside the allowed ones or with a wrong login repeatedly, **Then** access is refused or
   slowed down by the same lockout rules as the API.

---

### User Story 3 - Complete and trustworthy personal-data export (Priority: P2)

A parent or adult student can already download their data (phase 7). Phase 8 and 9 added new
personal data (receipts, payment instructions seen, online payment records, consents) after
that export was written. A GDPR export that silently omits data is a compliance defect, so
completeness must be checked, not assumed.

**Why this priority**: it is a legal obligation and the data model grew since the export was
built.

**Independent Test**: create a family with data in every personal-data table, export it, and
compare against an inventory of tables that hold personal data; the test fails if a table
holding personal data is neither exported nor explicitly listed as excluded with a reason.

**Acceptance Scenarios**:

1. **Given** a parent with children, lessons, payments, receipts, consents and online payment
   records, **When** they request the export, **Then** every personal-data item of theirs and of
   their children appears, and nothing belonging to another family or another studio does.
2. **Given** a new model that stores personal data and was added without export coverage,
   **When** the automated checks run, **Then** they fail and name the model.
3. **Given** a very large account, **When** the export is requested, **Then** it finishes
   within the agreed time or is produced in the background and delivered without blocking the
   request.
4. **Given** the export file, **When** a person opens it, **Then** it is in a common,
   readable format with field names understandable to a non-developer.

---

### User Story 4 - A portfolio a stranger can understand in ten minutes (Priority: P3)

The project exists to demonstrate production-grade backend skills. A reviewer opening the
repository must understand what it is, how it is built, what was decided and why, and how to
run it, without reading the whole study documentation.

**Why this priority**: it adds no behaviour, but it is the stated purpose of the project and
costs little once the other three stories are done.

**Independent Test**: a person who does not know the project reads only the top-level write-up
and answers five questions: what it does, the architecture in one sentence, three notable
design decisions, how to run the tests, what is deliberately not done.

**Acceptance Scenarios**:

1. **Given** the repository front page, **When** a reviewer reads it, **Then** it contains the
   problem, a one-picture architecture, the key decisions with links to their ADRs, honest
   measured numbers (tests, coverage, load test) and the limits.
2. **Given** a case study in English, **When** a reviewer reads it, **Then** it tells the story
   of three real problems found and solved, using the knowledge base entries, without invented
   numbers.
3. **Given** the commands in the write-up, **When** a reviewer runs them on a clean machine,
   **Then** they work as written.

### Edge Cases

- A deprecated endpoint is called by a client that ignores the signals: it must keep working
  until the removal date and only then answer with a clear "gone" response, never silently
  change.
- An operator account that loses its verification device: recovery is an operator command, not
  an admin screen that anyone could reach.
- An admin action on thousands of rows (bulk): it must be refused or capped for read-only
  records and audited once with the count.
- The export of a person who has already been erased (anonymised): it returns what is left and
  says so, it does not fail.
- Export requested twice at the same time: one export is produced, not two.
- The portfolio write-up mentions a number that later changes (test count): numbers come from
  a command or are dated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST publish a written API versioning and deprecation policy covering
  what is breaking, the minimum notice (stated in days), where notices appear, and how a new
  version is introduced next to the old one.
- **FR-002**: The system MUST be able to mark any endpoint as deprecated with a removal date;
  deprecated endpoints MUST keep their behaviour and MUST signal deprecation and removal date in
  every response, and in the published contract.
- **FR-002a**: Every deprecation MUST be recorded in a human-readable register (date
  announced, removal date, replacement, link to its migration report, status) and MUST NOT be
  accepted without a migration report; headers alone are not enough because people do not
  read headers.
- **FR-002b**: Each call to a deprecated endpoint MUST leave a structured log line (endpoint,
  client app and version if sent, no personal data) so the owner can see who still uses it
  before removing it.
- **FR-002c**: A scheduled check (not part of the pull-request pipeline, so it never blocks
  unrelated work) MUST fail when a removal date is 30 days away or passed and the endpoint is
  still present; the owner either removes it or extends the date with a written reason.
- **FR-002d**: The repository MUST contain a migration report template (what changes, why,
  affected clients, old vs new, steps per client, test checklist, timeline, rollback) and, for
  each deprecation, a note for the mobile branch listing what its developer must change.
- **FR-003**: After the removal date a removed endpoint MUST answer with a clear, stable
  "gone" error, not a generic not-found.
- **FR-004**: Automated checks MUST fail when a change to the published contract is breaking
  and not registered as such.
- **FR-005**: Admin access MUST be limited to operator accounts; studio owners, teachers,
  parents and students MUST be refused.
- **FR-006**: In production, operator access to the admin MUST require verified two-step
  verification.
- **FR-007**: Records that are final by design (collected payments, reversal entries,
  receipts, audit entries, consents) MUST be read-only in the admin: no add where it would
  bypass the services, no edit, no delete, no bulk delete.
- **FR-008**: Every state-changing admin action MUST write an audit entry (who, what, when,
  how many records).
- **FR-009**: Admin sign-in MUST follow the same lockout and rate-limit rules as the API sign-in.
- **FR-010**: Admin list screens MUST NOT show decrypted sensitive fields (encrypted notes,
  authentication secrets, bank identifiers) and MUST NOT leak other personal data in list
  columns beyond what an operator needs.
- **FR-011**: The personal-data export MUST include every personal-data item of the requester
  and of the children they are linked to, across every part of the system that stores personal
  data, including receipts, consents and online payment records.
- **FR-012**: An automated inventory check MUST fail when a model holding personal data is
  neither exported nor listed as excluded with a written reason.
- **FR-013**: The export MUST never contain data of another family, another studio, or secrets
  (authentication secrets, tokens, other people's identifiers).
- **FR-014**: The export MUST be produced in a common readable format with understandable
  field names, and large accounts MUST NOT block the request beyond an agreed time.
- **FR-015**: Each export request MUST be recorded in the audit log.
- **FR-016**: The repository front page MUST explain the problem, architecture, key decisions
  (linked), measured results and limits; a short English case study MUST tell three real
  problems and their solutions from the knowledge base.
- **FR-017**: Every number in the write-up MUST be real and reproducible by a command or be
  marked with its date and source; nothing may be invented.
- **FR-018**: The study documentation (Italian) MUST be updated: concept docs for versioning
  and for admin hardening, ADRs for the decisions, glossary, interview Q&A, index, OWASP walk,
  and the older docs that describe the admin or the export as current.

### Key Entities

- **Deprecation notice**: an endpoint, the date it was announced, the removal date, the
  replacement, and its migration report. Lives in code, in the contract and in the register,
  not in the database.
- **Migration report**: a document per deprecation that tells each client how to move to the
  replacement (another version or another service) and how to go back.
- **Operator**: an account allowed to use the admin; distinct from studio roles; has
  verified two-step verification.
- **Admin audit entry**: an entry of the existing audit log, written for admin actions.
- **Export inventory**: the list of personal-data models and, for each, "exported" or
  "excluded because ...".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A deprecated endpoint is announced at least the policy's notice period
  (stated in days) before removal, in 100% of responses and in the contract.
- **SC-001a**: No deprecation can exist without a migration report and a register row (a test
  fails otherwise); the scheduled check turns red at 30 days before removal, so the date is
  never reached unnoticed.
- **SC-002**: 100% of breaking contract changes in a test branch are caught by the automated
  checks before merge.
- **SC-003**: 0 non-operator accounts can reach the admin; 0 operator sessions reach it in
  production without verified two-step verification (proved by tests for every role).
- **SC-004**: 100% of final records are read-only in the admin (a test enumerates them).
- **SC-005**: 100% of models holding personal data are covered by the export inventory; adding
  an uncovered model fails the checks.
- **SC-006**: An export for an account with the largest realistic data set (one parent, three
  children, two years of weekly lessons) is delivered in under 10 seconds or in the
  background with a visible status.
- **SC-007**: A reviewer unfamiliar with the project answers the five questions of the
  independent test in under ten minutes of reading.
- **SC-008**: The full quality gate stays green and coverage stays at or above 90%.

## Assumptions

- The API version in use stays `v1`; this phase introduces the policy and the mechanism, not a
  `v2`. A `v2` is created only when the first real breaking change appears.
- Notice period for removal: 90 days minimum, since mobile app stores update slowly (owner may
  change it; it is one number in the policy).
- The admin is used only by the project operator (the owner); no studio staff ever uses it, so
  it can be strict without hurting users.
- Two-step verification reuses the TOTP built in phase 7; no new factor is added.
- The export already exists (phase 7, ADR-032); this phase audits and completes it rather than
  rebuilding it, and keeps the same endpoint and the same format family.
- Receipts are generated on the fly and hold no stored personal data beyond the payment
  (phase 8, ADR-035); the export lists them by reference.
- The write-up is in English for the repository front page and the case study (audience: external
  reviewers); study docs stay in Italian (owner's decision).
- The mobile branch is not changed here; it only consumes the contract. Any needed mobile
  change is noted in a follow-up file like in phase 7.
- Online payments stay switched off and in test mode; nothing here changes that.
- Out of scope: new product features, a `v2`, an admin redesign, deploy or release steps (no
  build, no deploy until the owner asks).
