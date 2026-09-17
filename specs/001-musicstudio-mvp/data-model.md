# Phase 1 Data Model: MusicStudio MVP

All models live under `backend/apps/<app>/models.py` per the app breakdown in `plan.md`.
Money fields use `DecimalField(max_digits=8, decimal_places=2)`. All models get
`created_at`/`updated_at` timestamps unless noted.

## User (`apps/accounts`)

Extends Django `AbstractUser` (keeps `username`/`email`/`password` machinery).

| Field | Type | Notes |
|---|---|---|
| `role` | `CharField` choices: `teacher`, `studio_owner`, `parent` | immutable after creation via API (admin-only to change) |
| `email` | `EmailField`, unique | used as login identifier |
| `preferred_language` | `CharField` choices: `en`, `it`, default `en` | server-known for email reminder localization |

`studio_owner` is a `role` value, not a separate table — see Teacher.is_owner below.

## Studio (`apps/studios`)

| Field | Type | Notes |
|---|---|---|
| `name` | `CharField` | e.g. "Studio di Musica Bianchi" |
| `owner` | FK → `Teacher`, null=True | set once an owner-role Teacher creates/claims the studio |

## Teacher (`apps/studios`)

| Field | Type | Notes |
|---|---|---|
| `user` | OneToOne → `User` | role MUST be `teacher` or `studio_owner` |
| `studio` | FK → `Studio`, null=True, blank=True | null = solo teacher, no studio |
| `is_owner` | `BooleanField`, default False | True only if `user.role == studio_owner` |

**Validation**: `is_owner=True` requires `studio` to be set (an owner always has a studio, even
if it's a studio of one).

## Student (`apps/students`)

| Field | Type | Notes |
|---|---|---|
| `first_name`, `last_name` | `CharField` | |
| `instrument` | `CharField` | free text, e.g. "Piano" |
| `teacher` | FK → `Teacher` | the student's assigned teacher |
| `is_active` | `BooleanField`, default True | soft-disable instead of delete |

## ParentAccount (`apps/students`)

| Field | Type | Notes |
|---|---|---|
| `user` | OneToOne → `User` | role MUST be `parent` |
| `students` | M2M → `Student` (through `ParentStudentLink`) | supports siblings (many students) and adult self-serve students (parent == the student themself, one link) |

## Package (`apps/packages`)

| Field | Type | Notes |
|---|---|---|
| `student` | FK → `Student` | |
| `total_lessons` | `PositiveSmallIntegerField` | e.g. 8 |
| `lessons_remaining` | `PositiveSmallIntegerField` | starts equal to `total_lessons`, clamped ≥ 0 |
| `purchase_date` | `DateField` | |
| `expiry_date` | `DateField`, null=True, blank=True | optional; MVP renewal is manual (Assumption in spec.md) |
| `price` | `Decimal` | |
| `status` | `CharField` choices: `active`, `expired`, `completed` (computed on save/read: `completed` when `lessons_remaining==0`, `expired` when past `expiry_date`, else `active`) | |

**Invariant**: `0 <= lessons_remaining <= total_lessons`, enforced by a `CheckConstraint` plus
the guarded decrement in `Lesson.mark_completed()` (see research.md).

**"Active package" for a Student** = most recent Package by `purchase_date` with
`status == active`.

## Lesson (`apps/lessons`)

| Field | Type | Notes |
|---|---|---|
| `student` | FK → `Student` | |
| `teacher` | FK → `Teacher` | denormalized from `student.teacher` at creation for query simplicity and to survive a student reassignment without rewriting history |
| `package` | FK → `Package`, null=True, blank=True | the package this lesson draws down; null = unpackaged/trial lesson |
| `start_time` | `DateTimeField` | timezone-aware |
| `duration_minutes` | `PositiveSmallIntegerField`, default 30 | |
| `status` | `CharField` choices: `scheduled`, `completed`, `cancelled`, `no_show` | default `scheduled` |
| `notes` | `TextField`, blank=True | progress note, visible to linked parent once lesson is completed |
| `reminder_sent_at` | `DateTimeField`, null=True | set by the Celery Beat sweep, makes it idempotent |

**State transitions**: `scheduled → completed | cancelled | no_show`. No transition out of a
terminal state via the API (fixing a mistake is an explicit admin action, not a normal user
flow, per spec — MVP doesn't require an "un-complete" flow).

**Business rule** (`mark_completed()`): only fires the Package decrement the first time a
Lesson transitions into `completed`; `cancelled`/`no_show` never decrement (spec Acceptance
Scenario 3).

## Payment (`apps/payments`)

| Field | Type | Notes |
|---|---|---|
| `student` | FK → `Student` | who the payment is for (kept even for standalone payments) |
| `package` | FK → `Package`, null=True, blank=True | null = standalone payment not tied to a package |
| `amount` | `Decimal` | |
| `date` | `DateField` | |
| `method` | `CharField` choices: `cash`, `bank_transfer`, `manual_entry` | |
| `status` | `CharField` choices: `paid`, `pending`, `overdue` | manually set/updated by the teacher for MVP (no gateway webhooks) |

**Validation**: if `package` is set, `package.student` MUST equal `student` (spec edge case —
"payment registered against mismatched package is rejected").

## Relationships summary

```text
User (role) ──1:1── Teacher ──FK studio──> Studio
                       │
                       └──FK teacher── Student ──FK student── Package ──FK package── Lesson
                                          │                                    │
User (role=parent) ──1:1── ParentAccount ─M2M (ParentStudentLink)             │
                                          └────────────────< FK student ── Payment
```

## Cross-cutting: queryset scoping (Constitution Principle I)

- **Teacher** (`is_owner=False`): `Student.objects.filter(teacher__user=request.user)`, and
  Lesson/Package/Payment filtered transitively through that Student set.
- **Studio owner** (`is_owner=True`): `Student.objects.filter(teacher__studio=request.user.teacher.studio)`.
- **Parent**: `Student.objects.filter(parentstudentlink__parent__user=request.user)`.

Every ViewSet's `get_queryset()` MUST use one of the three filters above based on
`request.user.role` — this is the single choke point Principle I's tests target.
