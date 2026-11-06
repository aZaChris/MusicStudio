"""Write use-cases for students."""

from typing import Any

from django.core.exceptions import ValidationError

from .models import Student


def create_student(*, user: Any, **fields: Any) -> Student:
    """A student always belongs to the teacher who creates it (owners included)."""
    teacher = getattr(user, "teacher", None)
    if teacher is None:
        raise ValidationError("Only users with a teacher profile can create students.")
    return Student.objects.create(teacher=teacher, **fields)
