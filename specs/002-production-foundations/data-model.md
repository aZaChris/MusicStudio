# Data Model Changes: Production Foundations (Phase 1)

No new entities. The full model is in `specs/001-musicstudio-mvp/data-model.md`.

## Indexes (FR-013)

| Model | Index | Serves |
|---|---|---|
| Lesson | `(teacher, start_time)` | weekly agenda, upcoming, dashboard |
| Lesson | `(start_time)` partial `WHERE status='scheduled' AND reminder_sent_at IS NULL` | reminder sweep |
| Payment | `(student, -date)` | latest payment status subquery, student detail |
| Payment | `(status)` | pending payments count, status filter |
| Package | `(student, -purchase_date)` partial `WHERE lessons_remaining > 0` | active package lookup |

## Constraints

- `Teacher`: new `CheckConstraint` `teacher_owner_has_studio`: `is_owner = false OR studio_id
  IS NOT NULL` (replaces the `save()` override that called `clean()`).

## Field behaviour

- `Package.lessons_remaining`: read-only through the API; set to `total_lessons` by
  `packages.services.create_package`; decremented only by `lessons.services.complete_lesson`.
- `Lesson.package`: must belong to `Lesson.student` (validated in `lessons.services`).
- `Payment.package`: must belong to `Payment.student` (single rule in `payments.services`,
  reused by the model's `clean()` for the admin; `save()` no longer calls `clean()`).

## State transitions (unchanged, now in services)

- Lesson: `scheduled → completed` (decrements package once, idempotent);
  `scheduled → cancelled | no_show`; a completed lesson cannot be cancelled.
- Reminder: `reminder_sent_at: NULL → timestamp`, claimed before sending (at-most-once).
