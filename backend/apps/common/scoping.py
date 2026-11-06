"""Tenant scoping — the single choke point for Constitution Principle I.

Every queryset that returns or accepts Student/Lesson/Package/Payment data goes through
`role_scoped_queryset`, both for reads (view querysets) and for writes (the querysets of
related fields a client can set, see `apps/common/serializers.py`).
"""

from typing import TYPE_CHECKING, Any

from django.db.models import Model, QuerySet

from apps.accounts.models import User

if TYPE_CHECKING:
    from apps.packages.models import Package
    from apps.students.models import Student


def role_scoped_queryset[M: Model](
    user: Any,
    base_qs: QuerySet[M],
    *,
    teacher_field: str,
    studio_field: str,
    parent_field: str,
) -> QuerySet[M]:
    """Filter `base_qs` to exactly what `user` may see, based on role.

    `teacher_field` / `studio_field` / `parent_field` are ORM lookup paths from the
    queryset's model to a Teacher, a Studio and a ParentAccount respectively.
    `user` is typed `Any` because DRF hands us `AnonymousUser` during schema generation.
    """
    role = getattr(user, "role", None)

    if role == User.Role.STUDIO_OWNER:
        teacher = getattr(user, "teacher", None)
        if teacher is None or teacher.studio_id is None:
            return base_qs.none()
        return base_qs.filter(**{studio_field: teacher.studio_id})

    if role == User.Role.TEACHER:
        teacher = getattr(user, "teacher", None)
        if teacher is None:
            return base_qs.none()
        return base_qs.filter(**{teacher_field: teacher})

    if role == User.Role.PARENT:
        parent_account = getattr(user, "parent_account", None)
        if parent_account is None:
            return base_qs.none()
        # Only this path crosses a many-to-many, which can duplicate rows.
        return base_qs.filter(**{parent_field: parent_account}).distinct()

    return base_qs.none()


def students_visible_to(user: Any) -> "QuerySet[Student]":
    from apps.students.models import Student

    return role_scoped_queryset(
        user,
        Student.objects.all(),
        teacher_field="teacher",
        studio_field="teacher__studio",
        parent_field="parent_accounts",
    )


def packages_visible_to(user: Any) -> "QuerySet[Package]":
    from apps.packages.models import Package

    return role_scoped_queryset(
        user,
        Package.objects.all(),
        teacher_field="student__teacher",
        studio_field="student__teacher__studio",
        parent_field="student__parent_accounts",
    )
