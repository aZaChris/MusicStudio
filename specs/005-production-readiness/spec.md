# Feature Specification: Production Readiness (Phase 4)

**Feature Branch**: `refactor/production-standards`
**Created**: 2026-11-06
**Status**: Draft
**Input**: User description: "Phase 4 — Production readiness: deploy on a self-hosted
platform with production settings; error tracking; structured logs; load testing with
recorded baselines; off-site backups plus an executed restore drill; full OWASP API Top 10
walk-through with fixes; token revocation (logout, compromised token invalidation); payment
webhook source allowlist (test mode only)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A user logs out and their session really ends (Priority: P1)

Today a signed-in user who "logs out" only forgets the token on their device: the token keeps
working until it expires (up to 14 days for the long-lived one). After this feature, logging
out makes the long-lived token unusable at once. An operator can also cut off every session
of one account (for example a stolen phone), and the account must sign in again.

**Why this priority**: it closes a real security gap (OWASP API2, broken authentication) that
an interviewer is likely to ask about, and it needs code, tests and a data change.

**Independent Test**: sign in, log out, try to renew the session with the old long-lived
token: refused. Revoke all sessions of an account: every outstanding long-lived token of
that account is refused, other accounts are unaffected.

**Acceptance Scenarios**:

1. **Given** a signed-in user, **When** they log out, **Then** their long-lived token can no
   longer be used to obtain new short-lived tokens.
2. **Given** a long-lived token that was already used once to renew (rotation), **When**
   someone replays the old one, **Then** it is refused.
3. **Given** an account with sessions on several devices, **When** an operator revokes all
   its sessions, **Then** every device must sign in again, and no other account is affected.
4. **Given** a logout request with a token that belongs to another user, **When** it is sent,
   **Then** it is refused and the other user's session is untouched.

---

### User Story 2 - The operator deploys the API to production and sees it is healthy (Priority: P1)

The owner deploys the API, the background workers and the scheduler to the self-hosted
platform from the repository, with production settings and secrets supplied by the platform
only. After a deploy, a health check tells whether the API, the database and the queue are
reachable. A broken deploy can be rolled back to the previous version.

**Why this priority**: everything else in the phase (monitoring, load test, backups) needs a
running production-like environment.

**Independent Test**: deploy from a clean checkout following the runbook only; the health
check reports healthy; a request with a missing required secret makes the app refuse to
start with a clear message instead of starting half-configured.

**Acceptance Scenarios**:

1. **Given** the runbook and the platform secrets, **When** the owner deploys, **Then** the
   API answers over HTTPS and the health check reports all dependencies as healthy.
2. **Given** a missing required secret, **When** the app starts, **Then** it stops with a
   message naming the missing setting (never its value).
3. **Given** a bad release, **When** the owner rolls back, **Then** the previous version
   serves traffic again within the time stated in the runbook.

---

### User Story 3 - Errors and logs are visible without reading the server console (Priority: P2)

When the API or a background job fails, the owner receives the error with enough context
(endpoint, studio, request id) to reproduce it, without personal data such as emails, tokens
or payment details. Every log line is machine-readable and carries the request id, so one
request can be followed across the API and the background jobs.

**Why this priority**: without visibility, production problems are found by users first.

**Independent Test**: trigger a deliberate error on a test endpoint/job: it appears in the
error tracker with the request id and without secrets; the matching log lines share that id.

**Acceptance Scenarios**:

1. **Given** an unhandled error in a request, **When** it happens, **Then** it is reported
   with the request id and tenant, and personal data and credentials are scrubbed.
2. **Given** any request, **When** it completes, **Then** one structured log line records
   method, route, status, duration and request id.
3. **Given** the error tracker is unreachable or not configured, **When** errors happen,
   **Then** the API keeps working and errors still reach the logs.

---

### User Story 4 - Data survives the loss of the server (Priority: P2)

The database is backed up automatically to storage outside the production server. The owner
has performed, and written down, a full restore into a fresh database and checked that the
data is complete.

**Why this priority**: an untested backup is not a backup; the restore drill is the proof.

**Independent Test**: run the restore procedure from the latest off-site backup into an empty
database; row counts of the main tables match the source at backup time; record the time it
took.

**Acceptance Scenarios**:

1. **Given** the schedule, **When** a day passes, **Then** a new encrypted backup exists
   off-site and backups older than the retention window are removed.
2. **Given** the latest backup, **When** the owner follows the restore runbook, **Then** a
   working database is rebuilt and the measured restore time is recorded.
3. **Given** a backup job failure, **When** it happens, **Then** the owner is alerted.

---

### User Story 5 - The owner knows how much load the API can take (Priority: P3)

A repeatable load test exercises the main endpoints (sign-in, lesson list, calendar,
dashboard, package list) with realistic data volume. Its results are recorded as the
baseline to compare future changes against.

**Why this priority**: useful evidence for the portfolio and for spotting regressions, but it
does not change behaviour for users.

**Independent Test**: run the load test against a production-like environment; a report with
throughput, median and 95th percentile latency and error rate per endpoint is saved in the
repository.

**Acceptance Scenarios**:

1. **Given** seeded realistic data, **When** the load test runs at the target concurrency,
   **Then** a report with per-endpoint results is produced and committed as the baseline.
2. **Given** an endpoint that misses the target, **When** the report is reviewed, **Then** the
   finding and its cause (or the decision to accept it) are documented.

---

### User Story 6 - Only the payment provider can call the payment webhook (Priority: P3)

Payment notifications are already signature-checked. As a second layer, notifications that
do not come from the provider's published addresses are refused before any processing.

**Why this priority**: defence in depth on the money path; small in size.

**Independent Test**: a correctly signed notification from a non-allowlisted address is
refused; the same notification from an allowlisted address is processed.

**Acceptance Scenarios**:

1. **Given** a notification from an address outside the allowlist, **When** it arrives,
   **Then** it is refused and logged, and nothing is processed.
2. **Given** the API runs behind the platform proxy, **When** the client address is checked,
   **Then** the real caller address is used, and a forged forwarding header from the client
   cannot bypass the check.
3. **Given** local development or tests, **When** the allowlist is disabled by setting,
   **Then** signature checking still applies.

---

### User Story 7 - Every OWASP API Top 10 risk has a verdict and evidence (Priority: P2)

The security walk-through covers all ten OWASP API risks for this API. Each risk has a
verdict (covered, partly covered, accepted), the evidence (test, setting, or document), and
the fix when a gap is found.

**Why this priority**: it is the security deliverable of the phase and a strong interview
topic.

**Independent Test**: open the walk-through: all ten entries are present, each links to a
test or setting that exists, and every "gap" found has either a fix or a recorded decision.

**Acceptance Scenarios**:

1. **Given** the walk-through, **When** it is reviewed, **Then** all ten risks have a verdict
   and evidence.
2. **Given** a gap found during the walk, **When** it is fixed, **Then** a test proves the fix.

### Edge Cases

- Logout called twice with the same token: second call is harmless (no error that leaks state).
- Revoked-token storage grows forever: expired entries are purged on a schedule.
- Short-lived tokens issued before a logout keep working until they expire (at most the
  configured short lifetime); this is an accepted, documented trade-off.
- Backup succeeds but the upload off-site fails: counted as a failed backup and alerted.
- Restore into a database with a different major version: the runbook states the supported
  version.
- Payment provider changes its address list: the list is a setting, updatable without code.
- Error tracker quota exhausted: sampling keeps the API unaffected.
- Load test against production with real users: forbidden; only production-like environments.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to log out, making their long-lived token unusable immediately.
- **FR-002**: A long-lived token that has been rotated MUST NOT be usable again.
- **FR-003**: An operator MUST be able to revoke all sessions of a single account.
- **FR-004**: Expired revocation records MUST be purged automatically.
- **FR-005**: The application MUST refuse to start in production when a required setting is
  missing, naming the setting and never printing its value.
- **FR-006**: A health endpoint MUST report the reachability of the database and the queue
  without exposing internal details to unauthenticated callers.
- **FR-007**: The deploy, rollback and secret-rotation procedures MUST be written in a
  runbook that a person can follow without help.
- **FR-008**: Unhandled errors in requests and background jobs MUST be reported to an error
  tracker with request id and tenant, with personal data and credentials scrubbed.
- **FR-009**: All production logs MUST be structured (one machine-readable object per line)
  and carry a request id that is also propagated to background jobs started by the request.
- **FR-010**: The database MUST be backed up at least daily, encrypted, to storage outside
  the production server, with a retention window of at least 7 daily and 4 weekly copies.
- **FR-011**: A restore drill MUST be executed and recorded (date, backup used, duration,
  verification result).
- **FR-012**: A repeatable load test MUST cover the main endpoints and produce a saved report.
- **FR-013**: The payment webhook MUST refuse requests from addresses outside a configurable
  allowlist, using the real client address behind the proxy.
- **FR-014**: The OWASP API Top 10 walk-through MUST cover all ten risks with verdict and
  evidence, and every gap fixed MUST have a test.
- **FR-015**: Every new behaviour MUST ship with tests, including cross-tenant tests where
  data is involved; the quality gate MUST stay green.
- **FR-016**: Study documentation in Italian (ADRs, concept docs, knowledge base, glossary,
  interview Q&A) MUST be produced for the phase.

### Key Entities

- **Revoked token record**: identifies a long-lived token that can no longer be used, with
  its owner and expiry, so it can be purged after expiry.
- **Backup**: an encrypted, dated copy of the database stored off-site, with retention class
  (daily/weekly).
- **Restore drill record**: date, backup used, duration, checks performed, outcome.
- **Load test baseline**: date, environment, concurrency, per-endpoint throughput, latency
  percentiles and error rate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After logout, 100% of attempts to renew a session with the old long-lived token
  are refused.
- **SC-002**: A new person can deploy from a clean checkout using only the runbook in under
  60 minutes.
- **SC-003**: A deliberate test error shows up in the error tracker within 1 minute, with
  zero credentials or emails in the report.
- **SC-004**: The restore drill rebuilds the database from the off-site copy in under 30
  minutes with row counts matching the source.
- **SC-005**: Under the target load (50 concurrent users), the main read endpoints keep a
  95th percentile response under 500 ms and an error rate under 1%; results recorded either way.
- **SC-006**: 10 of 10 OWASP API risks have a verdict and evidence in the walk-through.
- **SC-007**: Signed webhook notifications from non-allowlisted addresses are refused 100%
  of the time in tests.

## Assumptions

- Hosting is the owner's self-hosted platform (Coolify); no AWS services (constitution).
  The existing container definitions in the repository are the starting point.
- The error tracker is a hosted service on its free tier; the API works without it.
- Off-site storage is any S3-compatible bucket from a non-AWS provider; exact provider is a
  planning decision.
- Payments stay in provider test mode for the whole phase; real money is out of scope.
- Short-lived token lifetime stays short (current default 60 minutes; may be lowered in
  planning) because short-lived tokens are not individually revoked.
- The load test runs against a production-like environment with seeded synthetic data, never
  against real users' data.
- The frontend is out of scope; logout is an API capability.
- Out of scope for this phase (phase 5): API versioning/deprecation, admin hardening, GDPR
  export, portfolio write-up.
