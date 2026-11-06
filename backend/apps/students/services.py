"""Write use-cases for students."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.common.tenancy import TenantContext
from apps.studios.models import Teacher

from .models import Student


def create_student(ctx: TenantContext, **fields: Any) -> Student:
    """A student belongs to the teacher who creates it (owners included) and their studio."""
    if ctx.teacher_id is None or ctx.studio_id is None:
        raise ValidationError("Only users with a teacher profile can create students.")
    return Student.objects.create(teacher_id=ctx.teacher_id, studio_id=ctx.studio_id, **fields)


@transaction.atomic
def reassign_student(student: Student, teacher: Teacher) -> Student:
    """Give a student to another teacher of the same studio.

    Existing lessons keep their teacher: history stays truthful and the new teacher's
    agenda cannot be broken by lessons they never scheduled.
    """
    if teacher.studio_id != student.studio_id:
        raise ValidationError({"teacher": "The teacher must belong to the student's studio."})
    student.teacher = teacher
    student.save(update_fields=["teacher", "updated_at"])
    return student
