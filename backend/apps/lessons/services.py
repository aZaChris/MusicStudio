"""Write use-cases for lessons (Constitution III business-critical paths)."""

import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.packages.models import Package
from apps.students.models import Student

from .models import Lesson


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
    return Lesson.objects.create(
        student=student,
        teacher=student.teacher,
        package=package,
        start_time=start_time,
        duration_minutes=duration_minutes,
        notes=notes,
    )


def update_lesson(lesson: Lesson, **changes: Any) -> Lesson:
    for field, value in changes.items():
        setattr(lesson, field, value)
    if "student" in changes:
        lesson.teacher = lesson.student.teacher
    _ensure_package_matches_student(lesson.student, lesson.package)
    lesson.save()
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
    locked.save(update_fields=["status", "notes", "updated_at"])

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
