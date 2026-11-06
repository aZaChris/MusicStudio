# Data Model: Celery & Online Payments (Phase 3)

## payments.CheckoutSession (new)
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | used in the Stripe idempotency key and metadata |
| package | FK Package, CASCADE | |
| created_by | FK User, SET_NULL | who asked for the link |
| stripe_session_id | char, unique, null until created | `cs_test_…` |
| url | URL, blank | hosted page |
| amount | decimal(8,2) | package price at creation |
| currency | char(3) | `eur` |
| status | open / completed / failed / expired | |
| expires_at | datetime | from Stripe |
| created_at / updated_at | | |
Index: `(package, status)`; partial index `(expires_at) WHERE status='open'` for reconciliation.

## payments.WebhookEvent (new)
| Field | Type | Notes |
|---|---|---|
| stripe_event_id | char, unique | dedup key |
| type | char | e.g. `checkout.session.completed` |
| payload | JSON | raw event |
| received_at / processed_at | datetime | `processed_at` null until applied |
| attempts | int | processing attempts |
| last_error | text | |

## payments.Payment (changed)
- `Method.CARD = "card"` (online).
- `checkout`: OneToOne → CheckoutSession, null — at most one payment per attempt (DB-enforced).

## notifications.ReminderDelivery (new)
| Field | Type | Notes |
|---|---|---|
| lesson | FK Lesson, CASCADE | |
| parent | FK ParentAccount, CASCADE | |
| status | pending / sending / sent / failed / skipped | |
| attempts | int | |
| claimed_at | datetime null | lease start |
| sent_at | datetime null | |
| last_error | text | |
Unique `(lesson, parent)`; index `(status)`.

`Lesson.reminder_sent_at` stays as "sweep done for this lesson" marker.

## State machines
- CheckoutSession: `open → completed | failed | expired` (terminal).
- ReminderDelivery: `pending → sending → sent`; `sending → pending` (error, retry);
  `sending(stale) → sending` (re-claim); `→ failed` after max attempts; `→ skipped` if the
  lesson is no longer scheduled.
