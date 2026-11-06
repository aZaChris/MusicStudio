"""Write use-cases for lessons (Constitution III business-critical paths)."""

import datetime
from collections.abc import Callable
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F
from django.utils import timezone
from psycopg.errors import DeadlockDetected

from apps.common.exceptions import DomainConflict
from apps.packages.models import Package
from apps.students.models import Student

from .models import Lesson


class LessonOverlapError(DomainConflict):
    """The time slot is already taken by an active lesson (HTTP 409)."""

    code = "lesson_overlap"


# Constraint name → message. The database enforces the rule (ADR-009); we only translate.
OVERLAP_MESSAGES = {
    "lesson_no_teacher_overlap": "The teacher already has a lesson in this time slot.",
    "lesson_no_student_overlap": "The student already has a lesson in this time slot.",
}


# Concurrent inserts into the same slot can deadlock on the exclusion constraint: each
# transaction inserts its row, then waits for the other's uncommitted row while checking.
# PostgreSQL aborts one of them (SQLSTATE 40P01). Retrying the loser once is enough: the
# retry sees the winner's row and gets a normal constraint violation → 409.
MAX_DEADLOCK_RETRIES = 2


def _guarded_write[T](write: Callable[[], T]) -> T:
    """Run a lesson write in a savepoint; translate overlap violations into a 409.

    The savepoint keeps the surrounding transaction usable after the error.
    """
    for attempt in range(MAX_DEADLOCK_RETRIES + 1):
        try:
            with transaction.atomic():
                return write()
        except IntegrityError as exc:
            diag = getattr(exc.__cause__, "diag", None)
            constraint = getattr(diag, "constraint_name", None)
            if constraint in OVERLAP_MESSAGES:
                raise LessonOverlapError(OVERLAP_MESSAGES[constraint]) from exc
            raise
        except OperationalError as exc:
            if isinstance(exc.__cause__, DeadlockDetected) and attempt < MAX_DEADLOCK_RETRIES:
                continue
            raise
    raise AssertionError("unreachable")  # pragma: no cover


def end_of(start: datetime.datetime, minutes: int) -> datetime.datetime:
    """Real-time end of a lesson.

    Python adds a timedelta to an aware datetime on the *wall clock* of its time zone. DRF
    hands us Europe/Rome datetimes, so on the night clocks go back 02:30 CEST + 60 min
    would give 03:30 CET — two real hours later. Doing the arithmetic in UTC avoids it.
    """
    return start.astimezone(datetime.UTC) + datetime.timedelta(minutes=minutes)


def _ensure_package_matches_student(student: Student, package: Package | None) -> None:
    # Scoping alone would allow another student of the same teacher; completing such a
    # lesson would then decrement the wrong family's package.
    if package is not None and package.student_id != student.pk:
        raise ValidationError({"package": "Package must belong to the lesson's student."})


def create_lesson(
    *,
    student: Student,
    start_time: datetime.datetime,
    duration_minutes: int = 30,
    package: Package | None = None,
    notes: str = "",
) -> Lesson:
    """The teacher is always the student's teacher; the package defaults to the active one."""
    if package is None:
        package = student.active_package
    _ensure_package_matches_student(student, package)
    return _guarded_write(
        lambda: Lesson.objects.create(
            student=student,
            teacher=student.teacher,
            package=package,
            start_time=start_time,
            end_time=end_of(start_time, duration_minutes),
            notes=notes,
        )
    )


def update_lesson(lesson: Lesson, **changes: Any) -> Lesson:
    duration = changes.pop("duration_minutes", lesson.duration_minutes)
    for field, value in changes.items():
        setattr(lesson, field, value)
    lesson.end_time = end_of(lesson.start_time, duration)
    if "student" in changes:
        lesson.teacher = lesson.student.teacher
    _ensure_package_matches_student(lesson.student, lesson.package)
    _guarded_write(lesson.save)
    return lesson


@transaction.atomic
def complete_lesson(lesson: Lesson, *, note: str = "") -> Lesson:
    """Mark a lesson completed and draw down its package exactly once.

    Idempotent and safe under concurrency: the lesson row is locked, so a double submit
    waits for the first one and then sees `completed`. The package decrement is a single
    guarded UPDATE that can never go below zero.
    """
    locked = Lesson.objects.select_for_update().get(pk=lesson.pk)
    if locked.status == Lesson.Status.COMPLETED:
        return locked

    locked.status = Lesson.Status.COMPLETED
    if note:
        locked.notes = note
    # A cancelled lesson re-enters the agenda when completed: its slot may be taken.
    _guarded_write(lambda: locked.save(update_fields=["status", "notes", "updated_at"]))

    if locked.package_id is not None:
        Package.objects.filter(pk=locked.package_id, lessons_remaining__gt=0).update(
            lessons_remaining=F("lessons_remaining") - 1, updated_at=timezone.now()
        )
    return locked


CANCEL_STATUSES = (Lesson.Status.CANCELLED, Lesson.Status.NO_SHOW)


def cancel_lesson(lesson: Lesson, *, status: str) -> Lesson:
    """Cancel or mark no-show. A completed lesson stays completed (no refund of the package)."""
    if status not in CANCEL_STATUSES:
        raise ValidationError({"status": "Status must be 'cancelled' or 'no_show'."})
    if lesson.status == Lesson.Status.COMPLETED:
        return lesson
    lesson.status = status
    lesson.save(update_fields=["status", "updated_at"])
    return lesson
