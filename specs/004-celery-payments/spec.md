# Feature Specification: Celery & Online Payments (Phase 3)

**Feature Branch**: `refactor/production-standards`
**Created**: 2026-11-06
**Status**: Draft
**Input**: User description: "Roadmap phase 3: Celery reliability with idempotent tasks,
online payments with Stripe in test mode, idempotent webhooks, caching."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A parent pays a lesson package online (Priority: P1)

Today payments are only recorded by hand. After this feature a parent (or the teacher, to
send the link) asks to pay a package online and receives a payment page link from the
payment provider. Asking twice for the same package gives back the same open link instead
of creating a second payment attempt. A package that is already paid cannot be paid again.

**Why this priority**: online payment is the main new capability of the phase and the
reason the webhook and task work exists.

**Independent Test**: request a checkout for a package twice: one attempt, same link. Request
for an already paid package: refused. Without provider configuration: a clear "not
available" answer.

**Acceptance Scenarios**:

1. **Given** an unpaid package visible to the user, **When** they request a checkout,
   **Then** they receive a link to the provider's payment page for the package price.
2. **Given** an open checkout for that package, **When** they request again, **Then** they
   receive the same link and no new attempt is created.
3. **Given** a package already paid online or by hand, **When** a checkout is requested,
   **Then** it is refused with a conflict answer.
4. **Given** a package of another family or studio, **When** a checkout is requested,
   **Then** it is not found.
5. **Given** the provider is not configured, or configured with live (non-test) keys,
   **When** a checkout is requested, **Then** the service answers "not available"; live keys
   are refused at start-up.

---

### User Story 2 - The payment is recorded exactly once when the provider confirms it (Priority: P1)

The provider notifies MusicStudio when a payment completes. Notifications can arrive late,
twice, out of order, or be forged. After this feature only genuine notifications are
accepted, each notification is processed once no matter how many times it arrives, and a
completed checkout produces exactly one paid payment record linked to the package.

**Why this priority**: money records must be exact; duplicated or forged notifications are
the classic failure of payment integrations.

**Independent Test**: send the same signed notification three times: one payment record.
Send one with a wrong signature: refused, nothing recorded. Simulate a lost notification:
the periodic reconciliation records the payment anyway.

**Acceptance Scenarios**:

1. **Given** a genuine "checkout completed and paid" notification, **When** it arrives,
   **Then** it is acknowledged quickly and a paid payment is recorded for the package.
2. **Given** the same notification again (provider retry), **When** it arrives, **Then** it
   is acknowledged and nothing new is recorded.
3. **Given** a notification with a missing or invalid signature, **When** it arrives,
   **Then** it is refused and nothing is stored.
4. **Given** a checkout completed but the notification never arrived, **When** the
   periodic reconciliation runs, **Then** the payment is recorded once.
5. **Given** an expired checkout, **When** its notification or the reconciliation sees it,
   **Then** the attempt is marked expired and a new checkout can be requested.

---

### User Story 3 - Lesson reminders are reliable without duplicates (Priority: P2)

Phase 1 chose "at most once" reminders: a crash between claiming and sending lost the
reminder. After this feature each (lesson, parent) reminder is recorded as a delivery to
make; deliveries that fail are retried with increasing delays; a delivery already sent is
never sent again. A worker crash no longer loses reminders.

**Why this priority**: promised in phase 1 (ADR-008); parents rely on reminders.

**Independent Test**: run the sweep twice: one delivery per parent. Make the first send
fail: it is retried and sent once. Kill the process after claiming: the delivery is picked
up again later.

**Acceptance Scenarios**:

1. **Given** a lesson in the reminder window with two linked parents, **When** the sweep
   runs any number of times, **Then** exactly two deliveries exist.
2. **Given** a delivery whose send fails, **When** retries happen, **Then** it is sent at most
   once successfully, after increasing delays, and gives up after a maximum number of tries.
3. **Given** a delivery claimed by a worker that died, **When** enough time passes, **Then**
   another run picks it up.

---

### User Story 4 - Background work survives worker crashes (Priority: P2)

Tasks are acknowledged only after they finish, a crashed worker's tasks are redelivered,
workers take one task at a time, and every task has a time limit. Every task is safe to run
more than once.

**Independent Test**: configuration assertions; each task's idempotency proven by running it
twice in tests.

---

### User Story 5 - The dashboard is fast and never stale after a change (Priority: P2)

The teacher dashboard is the most-opened screen. After this feature it is served from a
cache when nothing changed, and any change to lessons, packages, payments or students of
the studio makes the next dashboard fresh.

**Independent Test**: open the dashboard twice: the second time uses almost no database
work. Complete a lesson: the next dashboard shows it.

**Acceptance Scenarios**:

1. **Given** an unchanged studio, **When** the dashboard is opened again within the cache
   lifetime, **Then** it is served from the cache.
2. **Given** any create/update/delete of a lesson, package, payment or student of the
   studio, **When** the dashboard is opened next, **Then** it reflects the change.
3. **Given** two studios, **When** one changes, **Then** the other's cache is unaffected.

---

### User Story 6 - Study documentation (Priority: P2)

Italian concept docs (idempotent Celery tasks, idempotent webhooks, online payments with
Stripe, caching), ADRs, glossary/Q&A updates, OWASP walk, copy to the Windows folder.

### Edge Cases

- Notification for an unknown checkout (another environment, deleted data): acknowledged and
  stored, not applied.
- Amount in the notification different from the package price (price edited meanwhile): the
  recorded payment uses the amount actually charged.
- Notification types we do not handle: acknowledged and stored, no effect.
- Checkout requested while the previous attempt is expired: a new attempt is created.
- Provider unreachable while creating a checkout: "not available" answer, no attempt stored.
- Cache unavailable: the dashboard is computed normally.
- Reminder for a lesson cancelled after the delivery was created: not sent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users who can see a package MUST be able to request an online checkout for it;
  the result is a provider payment page link for the package price in the studio currency.
- **FR-002**: Repeated checkout requests for a package with an open attempt MUST return the
  same attempt; requests to the provider MUST carry an idempotency key.
- **FR-003**: Checkout for a package that already has a paid payment MUST be refused (409).
- **FR-004**: Online payments MUST only be possible with test-mode credentials; live
  credentials MUST prevent start-up; missing credentials MUST make checkout "not available"
  (503) without affecting the rest of the API.
- **FR-005**: The notification endpoint MUST verify the provider signature and refuse
  invalid notifications (400) without storing them.
- **FR-006**: Every accepted notification MUST be stored once by its provider event id; a
  repeated notification MUST be acknowledged without being processed again.
- **FR-007**: Processing MUST happen in the background, be idempotent, retry transient
  failures, and record at most one payment per checkout attempt.
- **FR-008**: A periodic reconciliation MUST resolve checkout attempts left open past their
  expiry by asking the provider, recording missed payments and marking expired attempts.
- **FR-009**: Reminders MUST be recorded as one delivery per (lesson, parent), sent with
  retries and backoff, never sent twice once successful, and recoverable after a crash.
- **FR-010**: Background workers MUST acknowledge tasks late, redeliver tasks of crashed
  workers, prefetch one task at a time, and enforce time limits.
- **FR-011**: The studio dashboard (teachers and owners) MUST be cached per scope and
  invalidated by any write to the studio's lessons, packages, payments or students.
- **FR-012**: The phase MUST deliver Italian study docs, ADRs, an OWASP walk update, and the
  copy to the Windows study folder.

### Key Entities

- **CheckoutSession**: one online payment attempt for a package — provider session id, link,
  amount, expiry, status (open, completed, expired), resulting payment.
- **WebhookEvent**: one provider notification — provider event id (unique), type, payload,
  received and processed times.
- **ReminderDelivery**: one reminder to send — lesson, parent, status (pending, sending, sent,
  failed), attempts, last error, sent time.
- **Payment**: gains the method "card" and an optional link to its checkout attempt.

## Success Criteria *(mandatory)*

- **SC-001**: Sending the same genuine notification N times records exactly one payment.
- **SC-002**: 100% of notifications with an invalid signature are refused and not stored.
- **SC-003**: A checkout completed without notification is recorded within one
  reconciliation cycle (≤ 1 hour).
- **SC-004**: Running the reminder sweep N times creates one delivery per parent per lesson;
  a transient send failure still ends in exactly one sent email.
- **SC-005**: A cached dashboard request performs at most 2 database round-trips (vs 6).
- **SC-006**: Coverage stays ≥ 90%; four new concept docs of 800–1500 words.

## Assumptions

- Provider: Stripe, Checkout Sessions in `payment` mode, currency EUR, test mode only
  (constitution IV). No real Stripe account is available while building: provider calls are
  isolated behind one module and replaced by fakes in tests; signatures are generated with
  the real algorithm.
- The parent pays the whole package at once; partial payments and refunds are out of scope.
- A package counts as paid if any payment linked to it has status paid (manual or online).
- Success/cancel pages belong to the clients; the API receives their URLs from settings.
- Dashboard staleness up to the cache lifetime (5 minutes) is acceptable for time-based
  parts ("upcoming" lessons); data changes invalidate immediately.
- Parents' dashboards are not cached (rarely used, span several studios).
- The reminder outbox replaces the phase 1 at-most-once claim (ADR-008 superseded).
