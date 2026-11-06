# Data Model Changes: Domain Integrity (Phase 2)

## Studio (tenant)
- Unchanged fields. Every teacher and student now references one.
- Personal studio for solo teachers: `name = "<teacher email>"`, `owner = teacher`.

## Teacher
- `studio`: FK → Studio, **NOT NULL**, `on_delete=PROTECT` (was nullable, SET_NULL).
- Constraint `teacher_owner_has_studio` becomes redundant but is kept (harmless).
- Rule: at most `STUDIO_MAX_TEACHERS` (10) per studio — enforced by
  `studios.services.add_teacher_to_studio` (row lock on the studio).

## Student
- `studio`: new FK → Studio, NOT NULL, `on_delete=PROTECT`, indexed.
- Invariant: `student.studio_id == student.teacher.studio_id` (set by services on create and
  reassignment).

## Lesson
- `end_time`: new `DateTimeField`, NOT NULL. `duration_minutes` column **removed**; exposed
  as a property `(end_time - start_time) / 60s`.
- `CheckConstraint lesson_end_after_start`: `end_time > start_time`.
- `ExclusionConstraint lesson_no_teacher_overlap`: `teacher WITH =`,
  `tstzrange(start_time, end_time, '[)') WITH &&`, `WHERE status IN ('scheduled','completed')`.
- `ExclusionConstraint lesson_no_student_overlap`: same with `student`.
- Requires extension `btree_gist` (for `=` on bigint inside a GiST index).

## Payment
- Status transitions: `pending → paid`, `pending → overdue`, `overdue → paid`; `paid` final.

## Migrations (order)
1. `studios`: data migration — personal studios; then `Teacher.studio` NOT NULL/PROTECT.
2. `students`: add `studio` nullable → backfill from teacher → NOT NULL.
3. `lessons`: `BtreeGistExtension`; add `end_time` nullable → backfill
   `start_time + duration_minutes * interval '1 minute'` → NOT NULL → remove
   `duration_minutes` → check + exclusion constraints. Fails loudly if overlapping data exists.
