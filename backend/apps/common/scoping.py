"""Tenant scoping — the single choke point for Constitution Principle I.

The studio is the tenant (ADR-010). Every queryset that returns or accepts tenant data is
filtered here from the request's `TenantContext`, for reads (view querysets) and for writes
(related-field querysets, see `apps/common/serializers.py`):

- studio owner: everything whose studio is the owner's studio;
- teacher: everything attached to the teacher (a teacher belongs to exactly one studio);
- parent: everything about their linked children (children may be in different studios);
- anyone else: nothing.

Each model declares, once, how to reach studio / teacher / parent from it (`TenantPaths`).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db.models import Model, QuerySet

from .tenancy import TenantContext

if TYPE_CHECKING:
    from apps.packages.models import Package
    from apps.students.models import Student


@dataclass(frozen=True)
class TenantPaths:
    """ORM lookup paths from a model to its studio, teacher and parent account."""

    studio: str
    teacher: str
    parent: str


STUDENT_PATHS = TenantPaths(studio="studio", teacher="teacher", parent="parent_accounts")
# A lesson belongs to the teacher who gives it (kept when the student is reassigned).
LESSON_PATHS = TenantPaths(
    studio="student__studio", teacher="teacher", parent="student__parent_accounts"
)
# Packages and payments follow the student's current teacher.
STUDENT_CHILD_PATHS = TenantPaths(
    studio="student__studio", teacher="student__teacher", parent="student__parent_accounts"
)


def scope[M: Model](qs: QuerySet[M], ctx: TenantContext, paths: TenantPaths) -> QuerySet[M]:
    if ctx.is_owner:
        return qs.filter(**{paths.studio: ctx.studio_id})
    if ctx.is_teacher:
        return qs.filter(**{paths.teacher: ctx.teacher_id})
    if ctx.is_parent:
        # Only this path crosses a many-to-many, which can duplicate rows.
        return qs.filter(**{paths.parent: ctx.parent_id}).distinct()
    return qs.none()


def students_visible_to(ctx: TenantContext) -> "QuerySet[Student]":
    from apps.students.models import Student

    return scope(Student.objects.all(), ctx, STUDENT_PATHS)


def packages_visible_to(ctx: TenantContext) -> "QuerySet[Package]":
    from apps.packages.models import Package

    return scope(Package.objects.all(), ctx, STUDENT_CHILD_PATHS)
