"""Write use-cases for studios and their teachers."""

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Studio, Teacher

if TYPE_CHECKING:
    from apps.accounts.models import User


def ensure_studio_has_room(studio_id: int, *, joining_teacher_id: int | None = None) -> None:
    """A studio has at most STUDIO_MAX_TEACHERS teachers (product rule, 1-10 teachers)."""
    others = Teacher.objects.filter(studio_id=studio_id)
    if joining_teacher_id is not None:
        others = others.exclude(pk=joining_teacher_id)
    if others.count() >= settings.STUDIO_MAX_TEACHERS:
        raise ValidationError(
            {"studio": f"A studio cannot have more than {settings.STUDIO_MAX_TEACHERS} teachers."}
        )


@transaction.atomic
def add_teacher_to_studio(teacher: Teacher, studio: Studio) -> Teacher:
    """Move `teacher` into `studio`, respecting the teacher cap.

    The studio row is locked first: two concurrent joins are serialised, so the count
    cannot be read twice before either insert (which would allow an 11th teacher).
    """
    Studio.objects.select_for_update().get(pk=studio.pk)
    ensure_studio_has_room(studio.pk, joining_teacher_id=teacher.pk)
    if teacher.pk is not None and teacher.students.exclude(studio=studio).exists():
        raise ValidationError(
            {"teacher": "Reassign this teacher's students before moving them to another studio."}
        )
    teacher.studio = studio
    teacher.save()
    return teacher


@transaction.atomic
def create_solo_teacher(user: "User", *, studio_name: str | None = None) -> Teacher:
    """A teacher who works alone: a personal studio of one, owned by the teacher."""
    studio = Studio.objects.create(name=studio_name or user.email)
    teacher = Teacher.objects.create(user=user, studio=studio, is_owner=True)
    studio.owner = teacher
    studio.save(update_fields=["owner", "updated_at"])
    return teacher
