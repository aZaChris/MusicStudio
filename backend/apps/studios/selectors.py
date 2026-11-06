"""Read queries for studios (studio-owner only)."""

from typing import Any

from django.db.models import Count, QuerySet

from .models import Studio, Teacher


def _owner_studio_id(user: Any) -> int | None:
    teacher = getattr(user, "teacher", None)
    return teacher.studio_id if teacher is not None else None


def studio_for_owner(user: Any) -> Studio | None:
    studio_id = _owner_studio_id(user)
    if studio_id is None:
        return None
    return Studio.objects.annotate(teacher_count=Count("teachers")).filter(pk=studio_id).first()


def teachers_for_owner(user: Any) -> QuerySet[Teacher]:
    studio_id = _owner_studio_id(user)
    if studio_id is None:
        # Never filter(studio=None): that would list every solo teacher of every tenant.
        return Teacher.objects.none()
    return Teacher.objects.select_related("user").filter(studio_id=studio_id).order_by("id")
