# Feature Specification: Web Portal Hardening (Web 1)

**Feature Branch**: `refactor/production-standards`
**Created**: 2026-11-10
**Status**: Draft
**Input**: User description: "Web 1 — harden the React portal in frontend/: correct session
against rotating refresh tokens, safe deployment on Coolify without published ports, contract
types, all pages, visible errors, clean code for an external review, tests, CI, Italian study
docs. No new product features."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stay signed in, sign out for real (Priority: P1)

A teacher, studio owner or parent signs in on the web portal and keeps working for hours
without being thrown out. When they sign out, the session ends on the server, and the next
person on the same browser sees nothing of theirs.

**Why this priority**: today the portal logs users out after about 30 minutes because it does
not keep the renewed credentials the backend issues; sign-out leaves the session valid.

**Independent Test**: sign in, keep using the portal past several renewal windows, then sign
out and check that the previous session cannot be resumed and no previous data is shown.

**Acceptance Scenarios**:

1. **Given** a signed-in user, **When** the short access window expires repeatedly over an
   hour of use, **Then** the portal renews silently every time and the user is never sent to
   the login page.
2. **Given** several requests failing at the same moment because access expired, **When** the
   portal renews, **Then** it renews once and all requests complete.
3. **Given** a session that can no longer be renewed, **When** a request fails for that
   reason, **Then** the user lands on the login page with a short explanation.
4. **Given** any role, **When** the user signs out, **Then** the server ends the session,
   local credentials and cached data are erased, and the login page appears; if the server is
   unreachable, local data is erased anyway.
5. **Given** a stored session at page load, **When** the portal opens, **Then** it confirms the
   user and role with the server before showing role-specific pages.

---

### User Story 2 - A safe deployment on Coolify (Priority: P1)

The owner deploys the portal next to the API on Coolify. The portal is reachable only through
the platform's HTTPS proxy, never through a port opened on the server, and the browser is told
to refuse the common attacks a static site is exposed to.

**Why this priority**: the owner deploys on Coolify after a friend's review; an exposed port or
missing headers would fail that review.

**Independent Test**: build and start the production container; check that it publishes no
host port, runs without administrator rights, serves every route of the portal, answers its
health check and sends the security headers; check that the API accepts browser calls only
from the portal's address.

**Acceptance Scenarios**:

1. **Given** the production stack definition, **When** it is reviewed, **Then** no service
   publishes a host port; the portal is reachable only through the platform proxy.
2. **Given** the portal container, **When** it runs, **Then** it runs as a non-administrator
   user and its base images are pinned to explicit versions.
3. **Given** a user reloading a deep page such as the student list, **When** the page loads,
   **Then** the portal appears instead of a "not found" error.
4. **Given** any page of the portal, **When** it is served, **Then** the response forbids
   embedding in other sites, restricts scripts and connections to the portal itself and the
   API, and sets referrer, content-type and permissions protections.
5. **Given** a web page on another site, **When** it tries to call the API from a browser,
   **Then** the API refuses it; only the portal's address is allowed.

---

### User Story 3 - Correct and complete data, honest errors (Priority: P2)

Teachers and owners see all their students and payments, not only the first 25. Every server
refusal is explained in the user's language, and dates are the local ones.

**Why this priority**: silent truncation and silent failures make the portal look correct
while it is wrong.

**Independent Test**: with more than 25 students and payments, all appear; force a server
refusal and check the message; register a payment after midnight and check its date.

**Acceptance Scenarios**:

1. **Given** 40 students, **When** the roster opens, **Then** all 40 are listed.
2. **Given** the server refuses an action (invalid input, conflict, forbidden, not found),
   **When** it answers, **Then** a translated message explains it and nothing typed is lost.
3. **Given** a payment registered between 00:00 and 01:00 local time, **When** it is saved,
   **Then** it carries today's local date.
4. **Given** a page whose data fails to load, **When** it is shown, **Then** it states the
   problem and offers to retry, instead of staying blank.

---

### User Story 4 - Ready for an external review (Priority: P2)

A reviewer can clone the repository, read a README that explains the portal, run the checks
with one command each, and see the same checks pass in CI.

**Why this priority**: the owner's friend reviews the code before it goes to Coolify.

**Independent Test**: on a clean checkout, follow the README; every check passes locally and
in CI; the linter reports nothing.

**Acceptance Scenarios**:

1. **Given** a push, **When** CI runs, **Then** type checks, lint, tests, the production build
   and the contract check run for the portal and must pass.
2. **Given** the API contract changes, **When** the portal's types are not regenerated,
   **Then** the contract check fails.
3. **Given** the README, **When** a reviewer reads it, **Then** it explains what the portal
   does, how to run it, how it is deployed and which security choices were made and why.

---

### User Story 5 - Study material and security walk (Priority: P3)

The hardening is documented in Italian for study, including a security walk of the portal and
the recorded decision about where the renewal credential is kept.

**Why this priority**: the documentation is a deliverable of the project.

**Independent Test**: the docs index lists the new material; the security walk covers every
item with a verdict and evidence.

**Acceptance Scenarios**:

1. **Given** the study docs, **When** they are read, **Then** they explain the session fix,
   the deployment choices and the accepted risk on credential storage.

### Edge Cases

- Network down while signed in: a clear "cannot reach the server" message; the user is not
  signed out because of it.
- Two browser tabs: renewing in one tab must not sign the other out (both read the same stored
  credential; the second renewal uses the rotated one).
- Sign-out while access has expired: the renewal that precedes sign-out rotates the credential;
  sign-out must still end the newest session on the server.
- Role changed on the server since the last visit: the startup check routes to the right area.
- Browser language other than Italian or English: English.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The portal MUST keep the newest renewal credential after every renewal.
- **FR-002**: The portal MUST perform at most one renewal at a time, shared by concurrent
  requests.
- **FR-003**: The short-lived access credential MUST be kept only in memory.
- **FR-004**: Sign-out MUST end the session on the server and erase local credentials and all
  cached data, even if the server is unreachable; it MUST end the newest session when a
  renewal happened just before.
- **FR-005**: At load, a stored session MUST be confirmed with the server before role-specific
  pages are shown; an unreachable server MUST NOT sign the user out.
- **FR-006**: Refusals MUST be shown translated; requests refused by the server MUST NOT be
  retried automatically.
- **FR-007**: Roster and payments MUST include every item, beyond the server's page size.
- **FR-008**: Dates sent and shown MUST be local calendar dates.
- **FR-009**: Data shapes MUST come from the API's published contract, with an automatic check
  that detects drift.
- **FR-010**: The production portal MUST run without administrator rights, publish no host
  port, use pinned base images, serve every route, expose a health check and send security
  headers (anti-embedding, script and connection restrictions, referrer, content-type and
  permissions policies).
- **FR-011**: The API MUST accept browser calls only from the configured portal address.
- **FR-012**: Type checks, lint, tests, the production build and the contract check MUST run
  automatically on every push.
- **FR-013**: The README MUST explain usage, deployment and security choices.
- **FR-014**: Italian study docs (audit, ADRs, concept docs, security walk, glossary,
  interview Q&A, index) MUST be produced.

### Key Entities

- **Session**: renewal credential (persisted in the browser), access credential (memory), the
  verified user.
- **Portal deployment**: the container, its address, its security headers and the API's
  allowed origin.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can work for more than an hour with a 15-minute access window without
  seeing the login page.
- **SC-002**: After sign-out, the previous session cannot be resumed (verified against the
  server) and 0 pages show the previous user's data.
- **SC-003**: The production stack publishes 0 host ports for the portal and the API.
- **SC-004**: Every page response carries all required security headers.
- **SC-005**: With 40 students, 40 appear; a payment registered at 00:30 carries today's date.
- **SC-006**: Every refusal in the tested flows produces a visible translated message; 0
  silent failures.
- **SC-007**: A clean checkout passes all checks locally and in CI, with 0 lint findings.

## Assumptions

- The API keeps its current authentication (access + rotating refresh with blacklist); moving
  the renewal credential to an httpOnly cookie needs backend changes and is out of scope: an
  ADR records the accepted risk and the next step (owner decision).
- Portal and API live on separate addresses on Coolify (e.g. `app.` and `api.`); a reverse
  proxy putting both on one address would add a second proxy hop and break the API's
  client-address rules (ADR-021).
- The API address is fixed at build time; changing it means rebuilding the portal.
- No new product features: pages and actions stay those of the current portal.
- The real Coolify deployment and the friend's review are owner tasks; verification here uses
  the production container built locally if Docker is available, otherwise the production
  build served with the same configuration.
